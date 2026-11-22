"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Agent, toolLabel } from "@/lib/agents";
import { Badge } from "@/components/ui/Badge";
import { Button, buttonClass } from "@/components/ui/Button";

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Agent[]>("/agents")
      .then(setAgents)
      .catch((e: Error) => setError(e.message));
  }, []);

  async function remove(agent: Agent) {
    if (!confirm(`Delete "${agent.name}"? Its runs, documents and memory will be deleted too.`)) return;
    try {
      await api(`/agents/${agent.id}`, { method: "DELETE" });
      setAgents((list) => (list ?? []).filter((a) => a.id !== agent.id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not delete the agent");
    }
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Agents</h1>
        <Link href="/agents/new" className={buttonClass()}>New agent</Link>
      </div>

      {error && <p className="mb-4 text-red-600">{error}</p>}
      {!agents && !error && <p className="text-gray-500">Loading...</p>}
      {agents && agents.length === 0 && (
        <div className="rounded bg-white p-8 text-center text-gray-500 shadow-sm">
          You have no agents yet. Create your first one to get started.
        </div>
      )}

      {agents && agents.length > 0 && (
        <ul className="space-y-3">
          {agents.map((a) => (
            <li key={a.id} className="flex items-center justify-between rounded bg-white p-4 shadow-sm">
              <div>
                <div className="font-medium">{a.name}</div>
                <div className="mt-2 flex flex-wrap gap-1">
                  {a.tools.length === 0 && <span className="text-xs text-gray-400">No tools</span>}
                  {a.tools.map((t) => (
                    <Badge key={t} tone={a.permissions[t] === "blocked" ? "red" : a.permissions[t] === "ask" ? "amber" : "green"}>
                      {toolLabel(t)}
                    </Badge>
                  ))}
                </div>
              </div>
              <div className="flex gap-2">
                <Link href={`/agents/${a.id}`} className={buttonClass("secondary")}>Edit</Link>
                <Button variant="danger" onClick={() => remove(a)}>Delete</Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
