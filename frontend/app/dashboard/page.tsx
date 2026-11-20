"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function Dashboard() {
  const [data, setData] = useState<any>(null);
  useEffect(() => { api("/metrics").then(setData); }, []);
  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Dashboard</h1>
      <pre className="bg-white p-4 rounded">{JSON.stringify(data, null, 2)}</pre>
    </div>
  );
}