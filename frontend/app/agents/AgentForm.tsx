"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import {
  Agent,
  AgentInput,
  MODES,
  PermissionMode,
  TOOLS,
  ToolName,
  defaultMode,
} from "@/lib/agents";
import { Button } from "@/components/ui/Button";
import { Field, Input, Select, Textarea } from "@/components/ui/Field";

type ToolState = Record<ToolName, { enabled: boolean; mode: PermissionMode }>;

function initialTools(agent?: Agent): ToolState {
  const state = {} as ToolState;
  for (const t of TOOLS) {
    const saved = agent?.permissions[t.id];
    state[t.id] = {
      enabled: agent?.tools.includes(t.id) ?? false,
      mode: MODES.some((m) => m.id === saved) ? (saved as PermissionMode) : defaultMode(t.id),
    };
  }
  return state;
}

export default function AgentForm({ initial }: { initial?: Agent }) {
  const router = useRouter();
  const [name, setName] = useState(initial?.name ?? "");
  const [instructions, setInstructions] = useState(initial?.instructions ?? "");
  const [tools, setTools] = useState<ToolState>(() => initialTools(initial));
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  function setTool(id: ToolName, change: Partial<ToolState[ToolName]>) {
    setTools((prev) => ({ ...prev, [id]: { ...prev[id], ...change } }));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (!name.trim()) {
      setError("Please give the agent a name.");
      return;
    }
    const enabled = TOOLS.filter((t) => tools[t.id].enabled);
    const body: AgentInput = {
      name: name.trim(),
      instructions,
      tools: enabled.map((t) => t.id),
      permissions: Object.fromEntries(enabled.map((t) => [t.id, tools[t.id].mode])),
      schedule: initial?.schedule ?? null, // the Schedule page owns this field
    };
    setSaving(true);
    try {
      await api(initial ? `/agents/${initial.id}` : "/agents", {
        method: initial ? "PUT" : "POST",
        body: JSON.stringify(body),
      });
      if (!initial) {
        // Next.js keeps hidden pages alive, so clear the form for the next new agent.
        setName("");
        setInstructions("");
        setTools(initialTools());
      }
      router.push("/agents");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the agent");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="max-w-2xl">
      <section className="mb-6 rounded bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-lg font-semibold">Basics</h2>
        <Field label="Agent name">
          <Input value={name} onChange={(e) => setName(e.target.value)}
                 placeholder="Sales Analyst" maxLength={100} required />
        </Field>
        <Field label="Instructions" hint="Tells the agent how to behave, e.g. “Always report KPIs in INR”.">
          <Textarea rows={5} value={instructions}
                    onChange={(e) => setInstructions(e.target.value)} />
        </Field>
      </section>

      <section className="mb-6 rounded bg-white p-6 shadow-sm">
        <h2 className="mb-1 text-lg font-semibold">Tools and permissions</h2>
        <p className="mb-4 text-sm text-gray-500">
          Choose what the agent can use. “Ask first” pauses the run until you approve.
        </p>
        <ul className="divide-y">
          {TOOLS.map((t) => (
            <li key={t.id} className="flex items-center justify-between gap-4 py-3">
              <label className="flex flex-1 items-start gap-3">
                <input type="checkbox" className="mt-1" checked={tools[t.id].enabled}
                       onChange={(e) => setTool(t.id, { enabled: e.target.checked })} />
                <span>
                  <span className="block text-sm font-medium">{t.label}</span>
                  <span className="block text-xs text-gray-500">{t.hint}</span>
                </span>
              </label>
              <div className="w-32 shrink-0">
                <Select aria-label={`${t.label} permission`}
                        value={tools[t.id].mode} disabled={!tools[t.id].enabled}
                        onChange={(e) => setTool(t.id, { mode: e.target.value as PermissionMode })}>
                  {MODES.map((m) => (
                    <option key={m.id} value={m.id}>{m.label}</option>
                  ))}
                </Select>
              </div>
            </li>
          ))}
        </ul>
      </section>

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
      <div className="flex gap-3">
        <Button type="submit" disabled={saving}>
          {saving ? "Saving..." : initial ? "Save changes" : "Create agent"}
        </Button>
        <Button variant="secondary" onClick={() => router.push("/agents")}>Cancel</Button>
      </div>
    </form>
  );
}
