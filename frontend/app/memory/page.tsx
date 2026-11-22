"use client";
import { useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { useAgents } from "@/lib/useAgents";
import { AgentSelect } from "@/components/AgentSelect";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input, Select } from "@/components/ui/Field";

type Mem = { id: number; kind: "short" | "long"; content: string };
type Filter = "all" | "short" | "long";

const FILTERS: { id: Filter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "long", label: "Long-term" },
  { id: "short", label: "Short-term" },
];

export default function MemoryPage() {
  const { agents, error: agentsError } = useAgents();
  const [picked, setPicked] = useState<number | null>(null);
  const agentId = picked ?? agents?.[0]?.id ?? null;

  const [filter, setFilter] = useState<Filter>("all");
  const [items, setItems] = useState<Mem[] | null>(null);
  const [kind, setKind] = useState<"long" | "short">("long");
  const [content, setContent] = useState("");
  const [error, setError] = useState("");

  // Bumping `version` makes the list load again (after adding or deleting).
  const [version, setVersion] = useState(0);
  const reload = () => setVersion((v) => v + 1);

  useEffect(() => {
    if (agentId === null) return;
    let cancelled = false;
    api<Mem[]>(`/agents/${agentId}/memory${filter === "all" ? "" : `?kind=${filter}`}`)
      .then((d) => { if (!cancelled) setItems(d); })
      .catch((e) => { if (!cancelled) setError(errorMessage(e)); });
    return () => { cancelled = true; };
  }, [agentId, filter, version]);

  function choose(id: number) {
    setPicked(id);
    setItems(null);
    setError("");
  }

  async function add() {
    if (agentId === null || !content.trim()) return;
    setError("");
    try {
      await api(`/agents/${agentId}/memory`, { method: "POST", body: JSON.stringify({ kind, content }) });
      setContent("");
      reload();
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  async function remove(id: number) {
    if (agentId === null) return;
    try {
      await api(`/memory/${id}`, { method: "DELETE" });
      reload();
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  return (
    <div className="max-w-3xl">
      <h1 className="mb-1 text-2xl font-bold">Agent memory</h1>
      <p className="mb-6 text-sm text-gray-500">
        Long-term memory holds facts and preferences the agent keeps. Short-term memory is a short note
        about its most recent runs (the newest 20 are kept).
      </p>

      {agentsError && <p className="mb-4 text-red-600">{agentsError}</p>}
      {!agents && !agentsError && <p className="text-gray-500">Loading...</p>}
      {agents && <AgentSelect agents={agents} value={agentId} onChange={choose} />}

      {agentId !== null && (
        <>
          <section className="mb-6 rounded bg-white p-4 shadow-sm">
            <h2 className="mb-2 font-semibold">Add a memory</h2>
            <div className="flex gap-2">
              <Select value={kind} onChange={(e) => setKind(e.target.value as "long" | "short")} className="w-36 shrink-0">
                <option value="long">Long-term</option>
                <option value="short">Short-term</option>
              </Select>
              <Input
                value={content}
                onChange={(e) => setContent(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && add()}
                placeholder="e.g. Always report money in INR"
              />
              <Button onClick={add}>Save</Button>
            </div>
          </section>

          {error && <p className="mb-3 text-sm text-red-600">{error}</p>}

          <div className="mb-3 flex gap-2">
            {FILTERS.map((f) => (
              <button
                key={f.id}
                onClick={() => setFilter(f.id)}
                className={`rounded px-3 py-1 text-sm ${
                  filter === f.id ? "bg-gray-900 text-white" : "bg-white shadow-sm hover:bg-gray-100"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          <section className="rounded bg-white p-4 shadow-sm">
            {!items && <p className="text-gray-500">Loading...</p>}
            {items && items.length === 0 && <p className="text-gray-500">No memories yet.</p>}
            {items && items.length > 0 && (
              <ul>
                {items.map((m) => (
                  <li key={m.id} className="flex items-start justify-between gap-4 border-t py-2 first:border-t-0">
                    <span className="min-w-0">
                      <span className="mr-2"><Badge tone={m.kind === "long" ? "blue" : "gray"}>{m.kind === "long" ? "long-term" : "short-term"}</Badge></span>
                      <span className="break-words">{m.content}</span>
                    </span>
                    <Button variant="danger" onClick={() => remove(m.id)}>Delete</Button>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </div>
  );
}
