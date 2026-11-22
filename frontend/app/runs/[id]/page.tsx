"use client";
import Link from "next/link";
import { use, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Run, RunStep, formatDuration, formatTime, isActive, streamRun } from "@/lib/runs";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/runs/StatusBadge";
import { ApprovalCard } from "./ApprovalCard";
import { StepDetail } from "./StepDetail";
import { StepGraph } from "./StepGraph";

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

function upsertStep(run: Run, step: RunStep): Run {
  const steps = run.steps ?? [];
  const known = steps.some((s) => s.id === step.id);
  return { ...run, steps: known ? steps.map((s) => (s.id === step.id ? step : s)) : [...steps, step] };
}

export default function RunPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const runId = Number(id);
  const [run, setRun] = useState<Run | null>(null);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<number | null>(null);
  const [busyStep, setBusyStep] = useState<number | null>(null);
  const [now, setNow] = useState(() => Date.now());

  // Load the run, then follow it live. If the live stream is not available, poll instead.
  useEffect(() => {
    const controller = new AbortController();
    const stopped = () => controller.signal.aborted;

    async function follow() {
      try {
        let current = await api<Run>(`/runs/${runId}`);
        if (stopped()) return;
        setRun(current);
        if (!isActive(current.status)) return;
        try {
          await streamRun(runId, (event, data) => {
            if (event === "step") setRun((r) => (r ? upsertStep(r, data as RunStep) : r));
            if (event === "status") setRun((r) => (r ? { ...r, status: (data as Run).status } : r));
          }, controller.signal);
        } catch {
          /* stream unavailable or closed: fall back to polling below */
        }
        while (!stopped()) {
          current = await api<Run>(`/runs/${runId}`);
          if (stopped()) return;
          setRun(current);
          if (!isActive(current.status)) return;
          await wait(2000);
        }
      } catch (e) {
        if (!stopped()) setError(e instanceof Error ? e.message : "Could not load the run");
      }
    }

    follow();
    return () => controller.abort();
  }, [runId]);

  // Keeps the "running for" timer moving.
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  async function answer(step: RunStep, approve: boolean) {
    setBusyStep(step.id);
    try {
      await api(`/runs/${runId}/steps/${step.id}/${approve ? "approve" : "reject"}`, { method: "POST" });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not send your answer");
    } finally {
      setBusyStep(null);
    }
  }

  async function stop() {
    if (!confirm("Stop this run now?")) return;
    try {
      await api(`/runs/${runId}/stop`, { method: "POST" });
      setRun(await api<Run>(`/runs/${runId}`));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not stop the run");
    }
  }

  if (error && !run) {
    return (
      <div>
        <p className="mb-4 text-red-600">{error}</p>
        <Link href="/runs" className="text-blue-600 underline">Back to runs</Link>
      </div>
    );
  }
  if (!run) return <p className="text-gray-500">Loading...</p>;

  const steps = run.steps ?? [];
  const waiting = steps.filter((s) => s.status === "waiting_approval");
  const chosen = steps.find((s) => s.id === selected) ?? null;
  const active = isActive(run.status);

  return (
    <div className="mx-auto max-w-6xl">
      <Link href="/runs" className="text-sm text-blue-600 hover:underline">&larr; All runs</Link>
      <div className="mb-6 mt-2 flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="break-words text-2xl font-bold">{run.task}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-gray-600">
            <StatusBadge status={run.status} />
            <span>Agent: {run.agent_name ?? `#${run.agent_id}`}</span>
            <span>Started {formatTime(run.started)}</span>
            <span>{active ? "Running for" : "Took"} {formatDuration(run.started, run.ended, now)}</span>
          </div>
        </div>
        {active && <Button variant="danger" onClick={stop}>Stop run</Button>}
      </div>

      {error && <p className="mb-4 text-red-600">{error}</p>}

      {waiting.map((step) => (
        <div key={step.id} className="mb-4">
          <ApprovalCard step={step} busy={busyStep === step.id} onAnswer={(approve) => answer(step, approve)} />
        </div>
      ))}

      {run.status === "done" && (
        <div className="mb-6 rounded border border-green-300 bg-green-50 p-4">
          <div className="mb-1 text-xs font-medium uppercase text-green-800">Result</div>
          <p className="whitespace-pre-wrap break-words">{run.result}</p>
        </div>
      )}
      {run.status === "failed" && (
        <div className="mb-6 rounded border border-red-300 bg-red-50 p-4">
          <div className="mb-1 text-xs font-medium uppercase text-red-800">The run did not finish</div>
          <p className="whitespace-pre-wrap break-words text-red-900">{run.error ?? "Unknown error"}</p>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-5">
        <section className="lg:col-span-3">
          <h2 className="mb-3 font-semibold">Steps</h2>
          <StepGraph run={run} selectedId={selected} onSelect={setSelected} />
        </section>
        <section className="lg:col-span-2">
          <h2 className="mb-3 font-semibold">Details</h2>
          <div className="rounded bg-white p-4 shadow-sm lg:sticky lg:top-8">
            <StepDetail step={chosen} />
          </div>
        </section>
      </div>
    </div>
  );
}
