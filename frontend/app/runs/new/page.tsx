"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Agent } from "@/lib/agents";
import { LlmStatus, Run } from "@/lib/runs";
import { Button } from "@/components/ui/Button";
import { Field, Select, Textarea } from "@/components/ui/Field";

export default function NewRunPage() {
  const router = useRouter();
  const [agents, setAgents] = useState<Agent[] | null>(null);
  const [llm, setLlm] = useState<LlmStatus | null>(null);
  const [agentId, setAgentId] = useState("");
  const [task, setTask] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    // "?agent=3" (from the Agents page) picks the agent in advance.
    const wanted = new URLSearchParams(window.location.search).get("agent") ?? "";
    api<Agent[]>("/agents")
      .then((list) => {
        setAgents(list);
        setAgentId(list.some((a) => String(a.id) === wanted) ? wanted : String(list[0]?.id ?? ""));
      })
      .catch((e: Error) => setError(e.message));
    api<LlmStatus>("/llm/status").then(setLlm).catch(() => {});
  }, []);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const run = await api<Run>(`/agents/${agentId}/runs`, {
        method: "POST",
        body: JSON.stringify({ task }),
      });
      router.push(`/runs/${run.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start the run");
      setBusy(false);
    }
  }

  if (agents && agents.length === 0) {
    return (
      <div>
        <h1 className="mb-4 text-2xl font-bold">New run</h1>
        <p className="text-gray-600">
          You need an agent first.{" "}
          <Link href="/agents/new" className="text-blue-600 underline">Create one</Link>
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-2xl">
      <h1 className="mb-6 text-2xl font-bold">New run</h1>

      {llm && !llm.ok && (
        <div className="mb-4 rounded border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
          The language model is not ready: {llm.error ?? "unknown problem"}
        </div>
      )}
      {llm?.ok && <p className="mb-4 text-sm text-green-700">Model ready: {llm.model}</p>}

      <form onSubmit={submit} className="space-y-4 rounded bg-white p-6 shadow-sm">
        <Field label="Agent">
          <Select value={agentId} onChange={(e) => setAgentId(e.target.value)} required>
            {(agents ?? []).map((a) => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </Select>
        </Field>
        <Field label="Task" hint="Say what you want done, for example: Summarise Sales.csv and flag unusual rows.">
          <Textarea
            rows={5}
            value={task}
            onChange={(e) => setTask(e.target.value)}
            maxLength={2000}
            required
          />
        </Field>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <Button type="submit" disabled={busy || !agentId || !task.trim()}>
          {busy ? "Starting..." : "Start run"}
        </Button>
      </form>
    </div>
  );
}
