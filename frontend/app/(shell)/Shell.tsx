"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, clearToken, getToken } from "@/lib/api";

const NAV = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/agents", label: "Agents" },
  { href: "/runs", label: "Runs" },
  { href: "/knowledge", label: "Knowledge" },
  { href: "/memory", label: "Memory" },
  { href: "/schedule", label: "Schedule" },
];

export default function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<{ name: string } | null>(null);
  const isPublic = pathname === "/login";

  useEffect(() => {
    if (isPublic) return;
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    api("/auth/me").then(setUser).catch(() => {});
  }, [pathname, isPublic, router]);

  if (isPublic) return <>{children}</>;
  if (!user) return <div className="p-8 text-gray-500">Loading...</div>;

  return (
    <div className="flex min-h-screen">
      <aside className="w-56 bg-gray-900 text-white p-4 flex flex-col">
        <h1 className="text-xl font-bold mb-6">AgentOS</h1>
        <nav className="flex-1 space-y-1">
          {NAV.map((n) => (
            <Link
              key={n.href}
              href={n.href}
              className={`block rounded px-3 py-2 ${
                pathname.startsWith(n.href) ? "bg-gray-700" : "hover:bg-gray-800"
              }`}
            >
              {n.label}
            </Link>
          ))}
        </nav>
        <div className="text-sm text-gray-300">
          <div className="mb-2">{user.name}</div>
          <button
            onClick={() => { clearToken(); router.replace("/login"); }}
            className="underline"
          >
            Log out
          </button>
        </div>
      </aside>
      <main className="flex-1 p-8 bg-gray-50 text-gray-900">{children}</main>
    </div>
  );
}
