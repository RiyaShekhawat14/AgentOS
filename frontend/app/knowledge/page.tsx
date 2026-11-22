"use client";
import { useEffect, useState, type ChangeEvent } from "react";
import { api, errorMessage } from "@/lib/api";
import { useAgents } from "@/lib/useAgents";
import { AgentSelect } from "@/components/AgentSelect";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Field";

type Doc = { id: number; filename: string; chunks: number };
type Hit = { text: string; source: string; score: number };

export default function KnowledgePage() {
  const { agents, error: agentsError } = useAgents();
  const [picked, setPicked] = useState<number | null>(null);
  const agentId = picked ?? agents?.[0]?.id ?? null;

  const [docs, setDocs] = useState<Doc[] | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<Hit[] | null>(null);

  // Bumping `version` makes the list load again (after an upload or delete).
  const [version, setVersion] = useState(0);
  const reload = () => setVersion((v) => v + 1);

  useEffect(() => {
    if (agentId === null) return;
    let cancelled = false;
    api<Doc[]>(`/agents/${agentId}/knowledge`)
      .then((d) => { if (!cancelled) setDocs(d); })
      .catch((e) => { if (!cancelled) setError(errorMessage(e)); });
    return () => { cancelled = true; };
  }, [agentId, version]);

  function choose(id: number) {
    setPicked(id);
    setDocs(null);
    setHits(null);
    setMessage("");
    setError("");
  }

  async function upload(e: ChangeEvent<HTMLInputElement>) {
    const input = e.target;
    const file = input.files?.[0];
    if (!file || agentId === null) return;
    setBusy(true);
    setError("");
    setMessage("Reading and indexing the file. The first upload can take a minute...");
    try {
      const form = new FormData();
      form.append("file", file);
      const r = await api<{ filename: string; chunks: number }>(`/agents/${agentId}/knowledge`, {
        method: "POST",
        body: form,
      });
      setMessage(`Added ${r.filename} (${r.chunks} pieces indexed).`);
      reload();
    } catch (err) {
      setMessage("");
      setError(errorMessage(err));
    } finally {
      setBusy(false);
      input.value = "";
    }
  }

  async function remove(doc: Doc) {
    if (agentId === null || !confirm(`Delete "${doc.filename}" from this agent's knowledge?`)) return;
    try {
      await api(`/agents/${agentId}/knowledge/${doc.id}`, { method: "DELETE" });
      setHits(null);
      reload();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function search() {
    if (agentId === null || !query.trim()) return;
    setError("");
    try {
      setHits(await api<Hit[]>(`/agents/${agentId}/knowledge/search?q=${encodeURIComponent(query)}`));
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <div className="max-w-3xl">
      <h1 className="mb-1 text-2xl font-bold">Knowledge base</h1>
      <p className="mb-6 text-sm text-gray-500">
        Upload documents for an agent. When it works on a task, it reads the most relevant parts first.
      </p>

      {agentsError && <p className="mb-4 text-red-600">{agentsError}</p>}
      {!agents && !agentsError && <p className="text-gray-500">Loading...</p>}
      {agents && <AgentSelect agents={agents} value={agentId} onChange={choose} />}

      {agentId !== null && (
        <>
          <section className="mb-6 rounded bg-white p-4 shadow-sm">
            <h2 className="mb-2 font-semibold">Upload a document</h2>
            <input
              type="file"
              accept=".pdf,.txt,.csv,.md"
              onChange={upload}
              disabled={busy}
              className="text-sm"
            />
            <p className="mt-2 text-xs text-gray-500">PDF, TXT, CSV or MD, up to 10 MB. Scanned PDFs (pictures of text) cannot be read.</p>
            {message && <p className="mt-3 text-sm text-gray-700">{message}</p>}
            {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
          </section>

          <section className="mb-6 rounded bg-white p-4 shadow-sm">
            <h2 className="mb-2 font-semibold">Documents</h2>
            {!docs && <p className="text-gray-500">Loading...</p>}
            {docs && docs.length === 0 && <p className="text-gray-500">Nothing uploaded for this agent yet.</p>}
            {docs && docs.length > 0 && (
              <ul>
                {docs.map((d) => (
                  <li key={d.id} className="flex items-center justify-between gap-4 border-t py-2 first:border-t-0">
                    <span className="min-w-0 truncate">{d.filename}</span>
                    <span className="flex shrink-0 items-center gap-3">
                      <span className="text-sm text-gray-500">{d.chunks} pieces</span>
                      <Button variant="danger" onClick={() => remove(d)}>Delete</Button>
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="rounded bg-white p-4 shadow-sm">
            <h2 className="mb-2 font-semibold">Test the search</h2>
            <p className="mb-3 text-sm text-gray-500">Ask a question to see which parts of the documents the agent would read.</p>
            <div className="flex gap-2">
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && search()}
                placeholder="e.g. What were the Q3 sales?"
              />
              <Button onClick={search}>Search</Button>
            </div>
            {hits && hits.length === 0 && <p className="mt-3 text-gray-500">No documents to search yet.</p>}
            {hits?.map((h, i) => (
              <div key={i} className="mt-3 border-t pt-3">
                <div className="text-xs text-gray-500">{h.source} · match {Math.round(h.score * 100)}%</div>
                <div className="text-sm">{h.text}</div>
              </div>
            ))}
          </section>
        </>
      )}
    </div>
  );
}
