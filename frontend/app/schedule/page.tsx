"use client";
import { useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { parseUtc } from "@/lib/runs";
import { useAgents } from "@/lib/useAgents";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Field, Input, Select, Textarea } from "@/components/ui/Field";
import Link from "next/link";

type Schedule = {
  id: number;
  agent_id: number;
  agent_name: string;
  cron: string;
  label: string;
  task: string;
  enabled: boolean;
  next_run: string | null;
  last_run: string | null;
};

type Frequency = "day" | "weekday" | "week" | "hour";

const DAYS = [
  ["mon", "Monday"], ["tue", "Tuesday"], ["wed", "Wednesday"], ["thu", "Thursday"],
  ["fri", "Friday"], ["sat", "Saturday"], ["sun", "Sunday"],
];

// Builds the cron text the API expects, e.g. "0 9 * * mon" = every Monday at 09:00.
function buildCron(freq: Frequency, day: string, time: string): string {
  const [h, m] = time.split(":").map(Number);
  if (freq === "hour") return `${m} * * * *`;
  if (freq === "day") return `${m} ${h} * * *`;
  if (freq === "weekday") return `${m} ${h} * * mon-fri`;
  return `${m} ${h} * * ${day}`;
}

const when = (iso: string | null) => (iso ? parseUtc(iso).toLocaleString() : "—");

export default function SchedulePage() {
  const { agents, error: agentsError } = useAgents();
  const [items, setItems] = useState<Schedule[] | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [pickedAgent, setPickedAgent] = useState<number | null>(null);
  const agentId = pickedAgent ?? agents?.[0]?.id ?? null;
  const [freq, setFreq] = useState<Frequency>("week");
  const [day, setDay] = useState("mon");
  const [time, setTime] = useState("09:00");
  const [task, setTask] = useState("");

  // Bumping `version` makes the list load again (after any change).
  const [version, setVersion] = useState(0);
  const reload = () => setVersion((v) => v + 1);

  useEffect(() => {
    let cancelled = false;
    api<Schedule[]>("/schedules")
      .then((d) => { if (!cancelled) setItems(d); })
      .catch((e) => { if (!cancelled) setError(errorMessage(e)); });
    return () => { cancelled = true; };
  }, [version]);

  async function create() {
    if (agentId === null || !task.trim() || !time) return;
    setError("");
    setNotice("");
    try {
      await api("/schedules", {
        method: "POST",
        body: JSON.stringify({ agent_id: agentId, cron: buildCron(freq, day, time), task }),
      });
      setTask("");
      reload();
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  async function toggle(s: Schedule) {
    try {
      await api(`/schedules/${s.id}`, { method: "PATCH", body: JSON.stringify({ enabled: !s.enabled }) });
      reload();
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  async function remove(s: Schedule) {
    if (!confirm(`Delete this schedule for "${s.agent_name}"?`)) return;
    try {
      await api(`/schedules/${s.id}`, { method: "DELETE" });
      reload();
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  async function runNow(s: Schedule) {
    setError("");
    try {
      const r = await api<{ run_id: number }>(`/schedules/${s.id}/run-now`, { method: "POST" });
      setNotice(`Started run #${r.run_id}.`);
      reload();
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  return (
    <div className="max-w-3xl">
      <h1 className="mb-1 text-2xl font-bold">Schedule</h1>
      <p className="mb-6 text-sm text-gray-500">
        Run an agent&apos;s task automatically, for example every Monday at 9:00. Times are in India time
        (IST). A schedule only runs while the AgentOS server is running.
      </p>

      {agentsError && <p className="mb-4 text-red-600">{agentsError}</p>}

      {agents && agents.length === 0 && (
        <div className="mb-6 rounded bg-white p-6 text-gray-500 shadow-sm">
          You have no agents yet. <Link href="/agents/new" className="text-blue-600 underline">Create one</Link> first.
        </div>
      )}

      {agents && agents.length > 0 && (
        <section className="mb-6 rounded bg-white p-4 shadow-sm">
          <h2 className="mb-3 font-semibold">New schedule</h2>
          <Field label="Agent">
            <Select value={agentId ?? ""} onChange={(e) => setPickedAgent(Number(e.target.value))}>
              {agents.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
            </Select>
          </Field>
          <div className="flex flex-wrap gap-4">
            <div className="w-44">
              <Field label="How often">
                <Select value={freq} onChange={(e) => setFreq(e.target.value as Frequency)}>
                  <option value="hour">Every hour</option>
                  <option value="day">Every day</option>
                  <option value="weekday">Every weekday</option>
                  <option value="week">Every week</option>
                </Select>
              </Field>
            </div>
            {freq === "week" && (
              <div className="w-44">
                <Field label="Day">
                  <Select value={day} onChange={(e) => setDay(e.target.value)}>
                    {DAYS.map(([id, label]) => <option key={id} value={id}>{label}</option>)}
                  </Select>
                </Field>
              </div>
            )}
            <div className="w-36">
              <Field label={freq === "hour" ? "At minute (time ignored)" : "Time"}>
                <Input type="time" value={time} onChange={(e) => setTime(e.target.value)} />
              </Field>
            </div>
          </div>
          <Field label="Task" hint="What the agent should do each time, e.g. Analyze Sales.csv and report the top 3 products">
            <Textarea rows={3} value={task} onChange={(e) => setTask(e.target.value)} maxLength={2000} />
          </Field>
          <Button onClick={create} disabled={!task.trim() || !time}>Create schedule</Button>
        </section>
      )}

      {error && <p className="mb-3 text-sm text-red-600">{error}</p>}
      {notice && (
        <p className="mb-3 text-sm text-green-700">
          {notice} <Link href="/runs" className="underline">See runs</Link>
        </p>
      )}

      <section className="space-y-3">
        {!items && !error && <p className="text-gray-500">Loading...</p>}
        {items && items.length === 0 && (
          <div className="rounded bg-white p-6 text-center text-gray-500 shadow-sm">No schedules yet.</div>
        )}
        {items?.map((s) => (
          <div key={s.id} className="rounded bg-white p-4 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="font-medium">{s.agent_name}</span>
                <Badge tone={s.enabled ? "green" : "gray"}>{s.enabled ? s.label : "Paused"}</Badge>
              </div>
              <div className="flex gap-2">
                <Button variant="secondary" onClick={() => runNow(s)}>Run now</Button>
                <Button variant="secondary" onClick={() => toggle(s)}>{s.enabled ? "Pause" : "Resume"}</Button>
                <Button variant="danger" onClick={() => remove(s)}>Delete</Button>
              </div>
            </div>
            <p className="mt-2 text-sm">{s.task}</p>
            <p className="mt-2 text-xs text-gray-500">
              {s.enabled && <>Next run: {when(s.next_run)} · </>}Last run: {when(s.last_run)}
            </p>
          </div>
        ))}
      </section>
    </div>
  );
}
