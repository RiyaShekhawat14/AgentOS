import { Badge, type Tone } from "@/components/ui/Badge";
import { STEP_STATUS_LABEL } from "@/lib/runs";

const TONE: Record<string, Tone> = {
  running: "blue",
  waiting_approval: "amber",
  done: "green",
  failed: "red",
  blocked: "red",
  rejected: "red",
};

// Works for both run statuses and step statuses.
export function StatusBadge({ status }: { status: string }) {
  return <Badge tone={TONE[status] ?? "gray"}>{STEP_STATUS_LABEL[status] ?? status}</Badge>;
}
