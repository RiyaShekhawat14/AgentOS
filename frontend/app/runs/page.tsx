"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Run, formatTime } from "@/lib/runs";
import { buttonClass } from "@/components/ui/Button";
import { StatusBadge } from "@/components/runs/StatusBadge";

export default function RunsPage() {
  const [runs, setRuns] = useState<Run[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Run[]>("/runs")
      .then(setRuns)
      .catch((e: Error) => setError(e.message));
  }, []);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Runs</h1>
        <Link href="/runs/new" className={buttonClass()}>New run</Link>
      </div>

      {error && <p className="mb-4 text-red-600">{error}</p>}
      {!runs && !error && <p className="text-gray-500">Loading...</p>}
      {runs && runs.length === 0 && (
        <div className="rounded bg-white p-8 text-center text-gray-500 shadow-sm">
          No runs yet. Give one of your agents a task to see it work here.
        </div>
      )}

      {runs && runs.length > 0 && (
        <ul className="space-y-3">
          {runs.map((r) => (
            <li key={r.id}>
              <Link
                href={`/runs/${r.id}`}
                className="flex items-center justify-between gap-4 rounded bg-white p-4 shadow-sm hover:bg-gray-50"
              >
                <div className="min-w-0">
                  <div className="truncate font-medium">{r.task}</div>
                  <div className="mt-1 text-xs text-gray-500">
                    {r.agent_name ?? `Agent #${r.agent_id}`} · {formatTime(r.started)}
                  </div>
                </div>
                <StatusBadge status={r.status} />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
