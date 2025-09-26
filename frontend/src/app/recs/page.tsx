import { pingHealth } from "@/lib/api";

export default async function RecsPage() {
  let status = "unknown";
  try {
    const data = await pingHealth();
    status = data.status;
  } catch {
    status = "down";
  }

  return (
    <main className="mx-auto max-w-2xl p-6">
      <h1 className="text-2xl font-semibold mb-3">Recommendations</h1>
      <div className="rounded-xl border p-4">
        <p className="text-sm text-gray-500">API health</p>
        <p className="text-lg">{status === "ok" ? "API is up" : "API not reachable"}</p>
        <p className="mt-2 text-xs text-gray-400">
          Using {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}
        </p>
      </div>
    </main>
  );
}
