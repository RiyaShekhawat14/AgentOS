"use client";
import { ChangeEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/Button";

type CsvFile = { name: string; size: number };

const formatSize = (bytes: number) =>
  bytes < 1024 ? `${bytes} B` : bytes < 1024 * 1024 ? `${(bytes / 1024).toFixed(1)} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`;

/** CSV files the agent can read with the CSV reader tool (max 5 MB each). */
export function AgentFiles({ agentId }: { agentId: number }) {
  const [files, setFiles] = useState<CsvFile[] | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () =>
    api<CsvFile[]>(`/agents/${agentId}/files`)
      .then(setFiles)
      .catch((e: Error) => setError(e.message));

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agentId]);

  async function upload(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      const form = new FormData();
      form.append("file", file);
      await api(`/agents/${agentId}/files`, { method: "POST", body: form });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  async function remove(name: string) {
    if (!confirm(`Delete ${name}?`)) return;
    setError("");
    try {
      await api(`/agents/${agentId}/files/${encodeURIComponent(name)}`, { method: "DELETE" });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  }

  return (
    <section className="mt-8 max-w-2xl rounded bg-white p-6 shadow-sm">
      <h2 className="font-semibold">CSV files</h2>
      <p className="mb-4 mt-1 text-sm text-gray-500">
        The CSV reader tool can read these files. Only .csv files up to 5 MB are accepted.
      </p>

      {error && <p className="mb-3 text-sm text-red-600">{error}</p>}
      {!files && !error && <p className="text-sm text-gray-500">Loading...</p>}
      {files && files.length === 0 && <p className="mb-3 text-sm text-gray-500">No files uploaded yet.</p>}
      {files && files.length > 0 && (
        <ul className="mb-4 divide-y divide-gray-100">
          {files.map((f) => (
            <li key={f.name} className="flex items-center justify-between py-2 text-sm">
              <span className="min-w-0 truncate">
                {f.name} <span className="text-gray-400">({formatSize(f.size)})</span>
              </span>
              <Button variant="danger" onClick={() => remove(f.name)}>Delete</Button>
            </li>
          ))}
        </ul>
      )}

      <label className="inline-block">
        <input type="file" accept=".csv,text/csv" className="hidden" onChange={upload} disabled={busy} />
        <span
          className={`inline-block cursor-pointer rounded bg-gray-100 px-4 py-2 text-sm font-medium text-gray-800 hover:bg-gray-200 ${
            busy ? "opacity-50" : ""
          }`}
        >
          {busy ? "Uploading..." : "Upload CSV"}
        </span>
      </label>
    </section>
  );
}
