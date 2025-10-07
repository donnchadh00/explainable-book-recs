'use client'
import { useState, useEffect, useMemo } from 'react'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import PageShell from "../components/PageShell"

export default function SemanticSearchPage() {
  const [q, setQ] = useState('')
  const [results, setResults] = useState<any[] | null>(null)
  const [loading, setLoading] = useState(false)

  const searchParams = useSearchParams()
  const qp = useMemo(() => searchParams.get('q') ?? '', [searchParams])

  useEffect(() => {
    setQ(qp)
    setResults(null)
  }, [qp])

  async function run(query?: string) {
    const queryToUse = (query ?? q).trim()
    if (!queryToUse) return
    setLoading(true)
    setResults(null)
    const url = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/search/semantic?q=${encodeURIComponent(queryToUse)}`
    const res = await fetch(url)
    const data = await res.json()
    setResults(data.results)
    setLoading(false)
  }

  const recPresets = [
    { label: "Coming-of-age novels", q: "coming-of-age novel with moral growth and hardship" },
    { label: "Anti-war novels", q: "anti war novels" },
    { label: "Gothic domestic drama", q: "gothic novel with brooding atmosphere and isolated settings" },
  ]

  return (
    <PageShell>
        <div className="max-w-3xl mx-auto p-6 space-y-4">
        <h1 className="text-2xl font-semibold">Semantic Search</h1>

        <div className="mt-4 flex flex-wrap gap-2">
            {recPresets.map(p => (
            <Link
                key={p.label}
                href={`/search?q=${encodeURIComponent(p.q)}`}
                className="rounded-full border px-3 py-1 text-xs hover:bg-black/5 dark:hover:bg-white/10 transition"
            >
                {p.label}
            </Link>
            ))}
        </div>

        <div className="flex gap-2">
            <input
            className="border rounded px-3 py-2 w-full"
            value={q}
            onChange={e => setQ(e.target.value)}
            placeholder='e.g. "Victorian social novel", "dystopian novels"'
            />
            <button
            onClick={() => run()}
            className="px-4 py-2 rounded bg-black text-white disabled:opacity-50"
            disabled={!q || loading}
            >
            {loading ? 'Searching…' : 'Search'}
            </button>
        </div>

        {results && (
            <ul className="divide-y border rounded">
            {results.map((r) => (
                <li key={r.id} className="p-3">
                <div className="font-medium">
                    {r.title}{r.subtitle ? `: ${r.subtitle}` : ''}
                </div>
                <div className="text-sm opacity-70">
                    {r.author ? `by ${r.author} · ` : ""}Cosine ~ {r.cosine?.toFixed(3)}
                </div>
                </li>
            ))}
            </ul>
        )}
        </div>
    </PageShell>
  )
}
