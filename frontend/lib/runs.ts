import { getToken } from "@/lib/api";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type RunStatus = "running" | "waiting_approval" | "done" | "failed";
export type Json = Record<string, unknown>;

export type RunStep = {
  id: number;
  type: string; // plan | tool | observe
  tool: string | null;
  input: Json | null;
  output: Json | null;
  status: string; // running | waiting_approval | done | failed | blocked | rejected
  ms: number;
};

export type Run = {
  id: number;
  agent_id: number;
  agent_name: string | null;
  task: string;
  status: RunStatus;
  started: string | null;
  ended: string | null;
  result: string | null;
  error: string | null;
  steps: RunStep[] | null; // null in lists
};

export type LlmStatus = { ok: boolean; model: string; models?: string[]; error?: string | null };

export const isActive = (status: string) => status === "running" || status === "waiting_approval";

// The API sends UTC times without a "Z"; add it so the browser does not read them as local time.
export const parseUtc = (value: string) =>
  new Date(/[zZ]$|[+-]\d\d:?\d\d$/.test(value) ? value : `${value}Z`);

export function formatDuration(start: string | null, end: string | null, now: number): string {
  if (!start) return "";
  const seconds = Math.max(0, Math.round(((end ? parseUtc(end).getTime() : now) - parseUtc(start).getTime()) / 1000));
  return seconds < 60 ? `${seconds}s` : `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

export const formatTime = (value: string | null) => (value ? parseUtc(value).toLocaleString() : "");

/** Reads the live stream of a run (Server-Sent Events) with the login token. */
export async function streamRun(
  runId: number,
  onEvent: (event: string, data: unknown) => void,
  signal: AbortSignal,
): Promise<void> {
  const token = getToken();
  const res = await fetch(`${API}/runs/${runId}/stream`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    signal,
  });
  if (!res.ok || !res.body) throw new Error(`Live updates failed (${res.status})`);
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let end: number;
    while ((end = buffer.indexOf("\n\n")) !== -1) {
      const block = buffer.slice(0, end);
      buffer = buffer.slice(end + 2);
      const event = block.split("\n").find((l) => l.startsWith("event: "))?.slice(7);
      const data = block.split("\n").find((l) => l.startsWith("data: "))?.slice(6);
      if (event && data) onEvent(event, JSON.parse(data));
    }
  }
}

/** Short text shown under a step in the graph. */
export function stepSummary(step: RunStep): string {
  const out = step.output ?? {};
  if (step.type === "plan") {
    const plan = Array.isArray(out.plan) ? (out.plan as unknown[]) : [];
    return plan.length ? plan.map(String).join(" > ") : "Working step by step";
  }
  if (step.type === "observe") return String(out.answer ?? out.error ?? "");
  const first = Object.values(step.input ?? {})[0];
  return typeof first === "string" ? first.split("\n")[0] : JSON.stringify(step.input ?? {});
}

export const STEP_STATUS_LABEL: Record<string, string> = {
  running: "Running",
  waiting_approval: "Waiting for you",
  done: "Done",
  failed: "Failed",
  blocked: "Blocked",
  rejected: "Rejected",
};
