export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function pingHealth() {
  const res = await fetch(`${API_URL}/health`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return (await res.json()) as { status: string };
}
