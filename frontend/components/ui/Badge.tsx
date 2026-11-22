import type { ReactNode } from "react";

type Tone = "gray" | "green" | "amber" | "red";

const tones: Record<Tone, string> = {
  gray: "bg-gray-100 text-gray-700",
  green: "bg-green-100 text-green-800",
  amber: "bg-amber-100 text-amber-800",
  red: "bg-red-100 text-red-800",
};

export function Badge({ tone = "gray", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${tones[tone]}`}>
      {children}
    </span>
  );
}
