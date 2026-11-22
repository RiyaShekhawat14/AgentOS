"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, errorMessage } from "@/lib/api";
import { StatusBadge } from "@/components/runs/StatusBadge";

type Metrics = {
  agents: number;
  tasks_run: number;
  success_rate: number;
  avg_seconds: number;
  tool_calls: number;
  runs_per_day: { day: string; count: number }[];
  tool_usage: { tool: string; count: number }[];
  recent_runs: { id: number; task: string; status: string; agent: string }[];
};

// One blue for every bar: both charts count the same kind of thing, so they share a colour.
const BAR = "#2a78d6";
const AXIS = { fill: "#52514e", fontSize: 12 };
const GRID = "#e7e5e0";

// Last 7 days (oldest first), with 0 for days that had no runs. Days are UTC, like the API.
function lastSevenDays(rows: Metrics["runs_per_day"]) {
  const counts = new Map(rows.map((r) => [r.day, r.count]));
  return Array.from({ length: 7 }, (_, i) => {
    const key = new Date(Date.now() - (6 - i) * 86_400_000).toISOString().slice(0, 10);
    const label = new Date(`${key}T00:00:00Z`).toLocaleDateString(undefined, {
      weekday: "short", day: "numeric", timeZone: "UTC",
    });
    return { day: label, count: counts.get(key) ?? 0 };
  });
}

function Card({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded bg-white p-4 shadow-sm">
      <div className="text-sm text-gray-500">{label}</div>
      <div className="mt-1 text-3xl font-bold">{value}</div>
    </div>
  );
}

function AsTable({ head, rows }: { head: [string, string]; rows: (string | number)[][] }) {
  return (
    <details className="mt-3 text-sm text-gray-600">
      <summary className="cursor-pointer">Show as table</summary>
      <table className="mt-2 w-full text-left">
        <thead><tr><th className="py-1 font-medium">{head[0]}</th><th className="font-medium">{head[1]}</th></tr></thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-t"><td className="py-1">{r[0]}</td><td>{r[1]}</td></tr>
          ))}
        </tbody>
      </table>
    </details>
  );
}

export default function Dashboard() {
  const [m, setM] = useState<Metrics | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Metrics>("/metrics").then(setM).catch((e) => setError(errorMessage(e)));
  }, []);

  if (error) return <p className="text-red-600">{error}</p>;
  if (!m) return <p className="text-gray-500">Loading...</p>;

  const days = lastSevenDays(m.runs_per_day);
  const noRuns = m.tasks_run === 0;

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold">Dashboard</h1>

      <div className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-5">
        <Card label="Agents" value={m.agents} />
        <Card label="Tasks run" value={m.tasks_run} />
        <Card label="Success rate" value={noRuns ? "—" : `${m.success_rate}%`} />
        <Card label="Average time" value={noRuns ? "—" : `${m.avg_seconds}s`} />
        <Card label="Tool calls" value={m.tool_calls} />
      </div>

      <div className="mb-8 grid gap-6 lg:grid-cols-2">
        <section className="rounded bg-white p-4 shadow-sm">
          <h2 className="mb-3 font-semibold">Runs per day (last 7 days)</h2>
          <div role="img" aria-label="Bar chart of runs per day for the last 7 days">
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={days} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
                <CartesianGrid stroke={GRID} vertical={false} />
                <XAxis dataKey="day" tick={AXIS} tickLine={false} axisLine={{ stroke: GRID }} />
                <YAxis allowDecimals={false} tick={AXIS} tickLine={false} axisLine={false} />
                <Tooltip cursor={{ fill: "rgba(0,0,0,0.04)" }} formatter={(v) => [v, "Runs"]} />
                <Bar dataKey="count" fill={BAR} radius={[4, 4, 0, 0]} maxBarSize={24} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <AsTable head={["Day", "Runs"]} rows={days.map((d) => [d.day, d.count])} />
        </section>

        <section className="rounded bg-white p-4 shadow-sm">
          <h2 className="mb-3 font-semibold">Tool usage</h2>
          {m.tool_usage.length === 0 ? (
            <p className="py-16 text-center text-gray-500">No tool calls yet.</p>
          ) : (
            <>
              <div role="img" aria-label="Bar chart of how many times each tool was used">
                <ResponsiveContainer width="100%" height={Math.max(160, m.tool_usage.length * 44 + 40)}>
                  <BarChart data={m.tool_usage} layout="vertical" margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
                    <CartesianGrid stroke={GRID} horizontal={false} />
                    <XAxis type="number" allowDecimals={false} tick={AXIS} tickLine={false} axisLine={{ stroke: GRID }} />
                    <YAxis type="category" dataKey="tool" width={110} tick={AXIS} tickLine={false} axisLine={false} />
                    <Tooltip cursor={{ fill: "rgba(0,0,0,0.04)" }} formatter={(v) => [v, "Calls"]} />
                    <Bar dataKey="count" fill={BAR} radius={[0, 4, 4, 0]} maxBarSize={24} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <AsTable head={["Tool", "Calls"]} rows={m.tool_usage.map((t) => [t.tool, t.count])} />
            </>
          )}
        </section>
      </div>

      <section className="rounded bg-white p-4 shadow-sm">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-semibold">Recent runs</h2>
          <Link href="/runs" className="text-sm text-blue-600 underline">All runs</Link>
        </div>
        {m.recent_runs.length === 0 ? (
          <p className="text-gray-500">No runs yet. Start one from the Agents page.</p>
        ) : (
          <table className="w-full text-left">
            <thead className="text-sm text-gray-500">
              <tr><th className="py-2 font-medium">Task</th><th className="font-medium">Agent</th><th className="font-medium">Status</th></tr>
            </thead>
            <tbody>
              {m.recent_runs.map((r) => (
                <tr key={r.id} className="border-t">
                  <td className="py-2 pr-4"><Link href={`/runs/${r.id}`} className="text-blue-600 hover:underline">{r.task}</Link></td>
                  <td className="pr-4">{r.agent}</td>
                  <td><StatusBadge status={r.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
