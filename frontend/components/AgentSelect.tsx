import Link from "next/link";
import type { Agent } from "@/lib/agents";
import { Field, Select } from "@/components/ui/Field";

// Dropdown of the user's agents, or a hint to create one when there are none.
export function AgentSelect({
  agents,
  value,
  onChange,
}: {
  agents: Agent[];
  value: number | null;
  onChange: (id: number) => void;
}) {
  if (agents.length === 0) {
    return (
      <div className="rounded bg-white p-6 text-gray-500 shadow-sm">
        You have no agents yet.{" "}
        <Link href="/agents/new" className="text-blue-600 underline">Create one</Link> first.
      </div>
    );
  }
  return (
    <div className="max-w-xs">
      <Field label="Agent">
        <Select value={value ?? ""} onChange={(e) => onChange(Number(e.target.value))}>
          {agents.map((a) => (
            <option key={a.id} value={a.id}>{a.name}</option>
          ))}
        </Select>
      </Field>
    </div>
  );
}
