const isServer = typeof window === "undefined";

const serverBase = process.env.API_URL || "http://api:8000";
const clientBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const API_URL = isServer ? serverBase : clientBase;

export async function pingHealth() {
  const res = await fetch(`${API_URL}/health`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return (await res.json()) as { status: string };
}
