"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, setToken } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const body = mode === "login" ? { email, password } : { email, name, password };
      const res = await api(`/auth/${mode}`, { method: "POST", body: JSON.stringify(body) });
      setToken(res.token);
      router.replace("/dashboard");
    } catch (err: any) {
      setError(err.message);
    }
  }

  const input = "w-full border rounded px-3 py-2 mb-3";
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <form onSubmit={submit} className="bg-white p-8 rounded shadow w-96 text-gray-900">
        <h1 className="text-2xl font-bold mb-1">AgentOS</h1>
        <p className="text-gray-500 mb-6">{mode === "login" ? "Log in" : "Create account"}</p>
        {mode === "register" && (
          <input className={input} placeholder="Name" value={name}
                 onChange={(e) => setName(e.target.value)} required />
        )}
        <input className={input} type="email" placeholder="Email" value={email}
               onChange={(e) => setEmail(e.target.value)} required />
        <input className={input} type="password" placeholder="Password" value={password}
               onChange={(e) => setPassword(e.target.value)} required />
        {error && <p className="text-red-600 text-sm mb-3">{error}</p>}
        <button className="w-full bg-blue-600 text-white rounded py-2">
          {mode === "login" ? "Log in" : "Register"}
        </button>
        <button type="button" className="mt-4 text-sm text-blue-600 underline"
                onClick={() => setMode(mode === "login" ? "register" : "login")}>
          {mode === "login" ? "No account? Register" : "Have an account? Log in"}
        </button>
      </form>
    </div>
  );
}