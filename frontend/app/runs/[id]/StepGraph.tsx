import { toolLabel } from "@/lib/agents";
import { Run, RunStep, STEP_STATUS_LABEL, isActive, stepSummary } from "@/lib/runs";

const BORDER: Record<string, string> = {
  running: "border-blue-500",
  waiting_approval: "border-amber-500",
  done: "border-green-500",
  failed: "border-red-500",
  blocked: "border-red-500",
  rejected: "border-red-500",
};

function title(step: RunStep): string {
  if (step.type === "plan") return "Plan";
  if (step.type === "observe") return step.status === "done" ? "Final answer" : "Run failed";
  return toolLabel(step.tool ?? "tool");
}

function Node({
  heading, text, border, tag, selected, pulse, onClick,
}: {
  heading: string; text: string; border: string; tag?: string;
  selected?: boolean; pulse?: boolean; onClick?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={!onClick}
      className={`w-full rounded border-l-4 bg-white p-3 text-left shadow-sm ${border} ${
        selected ? "ring-2 ring-blue-400" : ""
      } ${pulse ? "animate-pulse" : ""} ${onClick ? "hover:bg-gray-50" : "cursor-default"}`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-medium">{heading}</span>
        {tag && <span className="text-xs text-gray-500">{tag}</span>}
      </div>
      {text && <div className="mt-1 line-clamp-2 break-words text-sm text-gray-600">{text}</div>}
    </button>
  );
}

const Arrow = () => (
  <div className="flex flex-col items-center text-gray-300" aria-hidden>
    <div className="h-4 w-px bg-gray-300" />
    <div className="text-xs leading-none">&#9660;</div>
  </div>
);

/** Vertical flow: Task > Plan > tool calls > Answer. Click a step to see its details. */
export function StepGraph({
  run, selectedId, onSelect,
}: { run: Run; selectedId: number | null; onSelect: (id: number) => void }) {
  const steps = run.steps ?? [];
  return (
    <div className="flex flex-col items-stretch">
      <Node heading="Task" text={run.task} border="border-gray-400" />
      {steps.map((step) => (
        <div key={step.id}>
          <Arrow />
          <Node
            heading={title(step)}
            text={stepSummary(step)}
            border={BORDER[step.status] ?? "border-gray-400"}
            tag={`${STEP_STATUS_LABEL[step.status] ?? step.status}${step.ms ? ` · ${(step.ms / 1000).toFixed(1)}s` : ""}`}
            selected={step.id === selectedId}
            pulse={step.status === "running"}
            onClick={() => onSelect(step.id)}
          />
        </div>
      ))}
      {isActive(run.status) && !steps.some((s) => s.status === "running" || s.status === "waiting_approval") && (
        <div>
          <Arrow />
          <Node heading="Thinking..." text="The agent is choosing its next move" border="border-blue-300" pulse />
        </div>
      )}
    </div>
  );
}
