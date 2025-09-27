import { pingHealth, listBooks } from "@/lib/api";

export default async function RecsPage() {
  let status = "unknown";
  try {
    const data = await pingHealth();
    status = data.status;
  } catch {
    status = "down";
  }

  let books: Awaited<ReturnType<typeof listBooks>> = []
  try {
    books = await listBooks();
  } catch {}

  return (
    <main className="mx-auto max-w-2xl p-6">
      <h1 className="text-2xl font-semibold mb-3">Recommendations</h1>
      <div className="rounded-xl border p-4 mb-6">
        <p className="text-sm text-gray-500">API health</p>
        <p className="text-lg">{status === "ok" ? "API is up" : "API not reachable"}</p>
      </div>
      <div className="rounded-xl border p-4">
        <p className="text-sm text-gray-500 mb-2">Your books (sample)</p>
        <ul className="list-disc pl-5">
          {books.slice(0, 10).map(b => (
            <li key={b.id}>{b.title}{b.author ? ` — ${b.author}` : ""}</li>
          ))}
        </ul>
      </div>
    </main>
  );
}
