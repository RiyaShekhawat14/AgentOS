import { toolLabel } from "@/lib/agents";
import { RunStep } from "@/lib/runs";
import { Button } from "@/components/ui/Button";

export function ApprovalCard({
  step, busy, onAnswer,
}: { step: RunStep; busy: boolean; onAnswer: (approve: boolean) => void }) {
  return (
    <div className="rounded border border-amber-300 bg-amber-50 p-4">
      <div className="font-semibold text-amber-900">
        The agent wants to use {toolLabel(step.tool ?? "a tool")}
      </div>
      <p className="mt-1 text-sm text-amber-900">
        This tool is set to ask first. The run is paused until you answer.
      </p>
      <pre className="mt-3 max-h-48 overflow-auto rounded bg-white p-3 text-xs text-gray-800">
        {JSON.stringify(step.input ?? {}, null, 2)}
      </pre>
      <div className="mt-3 flex gap-2">
        <Button disabled={busy} onClick={() => onAnswer(true)}>Approve</Button>
        <Button variant="danger" disabled={busy} onClick={() => onAnswer(false)}>Reject</Button>
      </div>
    </div>
  );
}
