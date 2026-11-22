import { toolLabel } from "@/lib/agents";
import { RunStep, STEP_STATUS_LABEL } from "@/lib/runs";
import { StatusBadge } from "@/components/runs/StatusBadge";

const pretty = (value: unknown) => JSON.stringify(value, null, 2);

export function StepDetail({ step }: { step: RunStep | null }) {
  if (!step) {
    return <p className="text-sm text-gray-500">Click a step in the graph to see what the agent sent and received.</p>;
  }
  const { thought, ...output } = step.output ?? {};
  const label = step.type === "tool" ? toolLabel(step.tool ?? "tool") : step.type === "plan" ? "Plan" : "Final step";
  return (
    <div className="space-y-3 text-sm">
      <div className="flex items-center gap-2">
        <span className="font-semibold">{label}</span>
        <StatusBadge status={step.status} />
        {step.ms > 0 && <span className="text-gray-500">{(step.ms / 1000).toFixed(1)}s</span>}
      </div>
      {typeof thought === "string" && thought && (
        <div>
          <div className="mb-1 text-xs font-medium uppercase text-gray-500">Why</div>
          <p>{thought}</p>
        </div>
      )}
      {step.input && (
        <div>
          <div className="mb-1 text-xs font-medium uppercase text-gray-500">Input</div>
          <pre className="max-h-48 overflow-auto rounded bg-gray-900 p-3 text-xs text-gray-100">{pretty(step.input)}</pre>
        </div>
      )}
      {Object.keys(output).length > 0 && (
        <div>
          <div className="mb-1 text-xs font-medium uppercase text-gray-500">
            {step.type === "tool" ? "Output" : "Details"}
          </div>
          <pre className="max-h-72 overflow-auto rounded bg-gray-900 p-3 text-xs text-gray-100">{pretty(output)}</pre>
        </div>
      )}
      {!step.input && Object.keys(output).length === 0 && (
        <p className="text-gray-500">{STEP_STATUS_LABEL[step.status] ?? step.status}... nothing to show yet.</p>
      )}
    </div>
  );
}
