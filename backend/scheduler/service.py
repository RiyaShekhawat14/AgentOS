"""K5 Scheduler: runs an agent's task automatically on a repeating schedule.

How it works:
  * Every row in the `schedules` table becomes one APScheduler job.
  * When the job fires it does exactly what POST /agents/{id}/runs does:
    create a run and launch it in the background (Riya's runs service).
  * Schedules are cron strings. The Schedule page builds them from simple choices.
    Use day NAMES (mon, tue...) - APScheduler counts numeric weekdays differently from cron.
"""
import logging
import os
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.db.models import Agent, Schedule
from backend.db.session import SessionLocal
from backend.runs import service as runs_service

log = logging.getLogger("agentos.scheduler")

TIMEZONE = os.getenv("SCHEDULE_TZ", "Asia/Kolkata")
scheduler = BackgroundScheduler(timezone=TIMEZONE)

DAYS = {"mon": "Monday", "tue": "Tuesday", "wed": "Wednesday", "thu": "Thursday",
        "fri": "Friday", "sat": "Saturday", "sun": "Sunday"}


def make_trigger(cron: str) -> CronTrigger:
    """Turn a cron string into a trigger. Raises ValueError if it is not valid."""
    parts = cron.split()
    if len(parts) != 5:
        raise ValueError("Schedule must have 5 parts: minute hour day month weekday")
    return CronTrigger.from_crontab(cron, timezone=TIMEZONE)


def next_run_time(cron: str) -> str | None:
    trigger = make_trigger(cron)
    nxt = trigger.get_next_fire_time(None, datetime.now(trigger.timezone))
    return nxt.isoformat() if nxt else None


def describe(cron: str) -> str:
    """Plain-English label for the cron strings the Schedule page creates."""
    try:
        minute, hour, dom, month, dow = cron.split()
        if dom == "*" and month == "*" and minute.isdigit():
            if hour == "*" and dow == "*":
                return f"Every hour at :{int(minute):02d}"
            if hour.isdigit():
                at = f"{int(hour):02d}:{int(minute):02d}"
                if dow == "*":
                    return f"Every day at {at}"
                if dow == "mon-fri":
                    return f"Every weekday at {at}"
                if dow in DAYS:
                    return f"Every {DAYS[dow]} at {at}"
    except ValueError:
        pass
    return cron


def fire(schedule_id: int) -> None:
    """Called by APScheduler (in a background thread) when a schedule is due."""
    db = SessionLocal()
    try:
        sch = db.get(Schedule, schedule_id)
        agent = db.get(Agent, sch.agent_id) if sch else None
        if sch is None or agent is None or not sch.enabled:
            remove_job(schedule_id)
            return
        run = runs_service.create_run(db, agent, sch.task)
        runs_service.launch(db.get_bind(), run.id)
        sch.last_run = datetime.utcnow()
        db.commit()
        log.info("Schedule %s started run %s", schedule_id, run.id)
    except Exception:
        log.exception("Schedule %s failed to start", schedule_id)
    finally:
        db.close()


def _job_id(schedule_id: int) -> str:
    return f"schedule-{schedule_id}"


def add_job(schedule: Schedule) -> None:
    scheduler.add_job(fire, make_trigger(schedule.cron), args=[schedule.id],
                      id=_job_id(schedule.id), replace_existing=True, misfire_grace_time=300)


def remove_job(schedule_id: int) -> None:
    if scheduler.get_job(_job_id(schedule_id)):
        scheduler.remove_job(_job_id(schedule_id))


def sync_job(schedule: Schedule) -> None:
    """Make the running job match the database row (add, or remove when disabled)."""
    if schedule.enabled:
        add_job(schedule)
    else:
        remove_job(schedule.id)


def start() -> None:
    """Called when the API starts: load every enabled schedule and start the clock."""
    db = SessionLocal()
    try:
        for sch in db.query(Schedule).filter(Schedule.enabled.is_(True)).all():
            try:
                add_job(sch)
            except ValueError:
                log.warning("Skipping schedule %s: invalid cron '%s'", sch.id, sch.cron)
    finally:
        db.close()
    if not scheduler.running:
        scheduler.start()


def stop() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
