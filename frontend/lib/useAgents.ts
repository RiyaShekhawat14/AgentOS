"use client";
import { useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import type { Agent } from "@/lib/agents";

// Loads the logged-in user's agents (used by the Knowledge, Memory and Schedule pages).
export function useAgents() {
  const [agents, setAgents] = useState<Agent[] | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api<Agent[]>("/agents")
      .then(setAgents)
      .catch((e) => setError(errorMessage(e)));
  }, []);
  return { agents, error };
}
