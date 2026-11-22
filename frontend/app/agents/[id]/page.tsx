"use client";
import { use, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Agent } from "@/lib/agents";
import AgentForm from "../AgentForm";
import { AgentFiles } from "./AgentFiles";

export default function EditAgentPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [agent, setAgent] = useState<Agent | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Agent>(`/agents/${id}`)
      .then(setAgent)
      .catch((e: Error) => setError(e.message));
  }, [id]);

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold">Edit agent</h1>
      {error && <p className="text-red-600">{error}</p>}
      {!agent && !error && <p className="text-gray-500">Loading...</p>}
      {agent && <AgentForm key={agent.id} initial={agent} />}
      {agent && <AgentFiles agentId={agent.id} />}
    </div>
  );
}
