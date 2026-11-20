const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const getToken = () =>
  typeof window === "undefined" ? null : localStorage.getItem("token");
export const setToken = (t: string) => localStorage.setItem("token", t);
export const clearToken = () => localStorage.removeItem("token");

export async function api<T = any>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(`${API}${path}`, { ...options, headers });
  if (res.status === 401 && !path.startsWith("/auth/login")) {
    clearToken();
    if (typeof window !== "undefined") window.location.href = "/login";
    throw new Error("Not logged in");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Error ${res.status}`);
  }
  return res.json();
}