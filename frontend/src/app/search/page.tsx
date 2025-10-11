'use client'

import { useState, useEffect, useMemo } from 'react'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import PageShell from '../components/PageShell'
import Button from '../components/ui/Button'
import BookList, { BookListItem } from '../components/BookList'

interface RecResult {
  id: number
  title: string
  author?: string | null
  published_year?: number | null
  subtitle?: string | null
  cosine?: number
}

export default function SemanticSearchPage() {
  const [q, setQ] = useState('')
  const [results, setResults] = useState<RecResult[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const searchParams = useSearchParams()
  const qp = useMemo(() => searchParams.get('q') ?? '', [searchParams])

  useEffect(() => {
    setQ(qp)
    setResults(null)
    setError(null)
    if (qp) {
      run(qp)
    }
  }, [qp])

  async function run(query?: string) {
    const queryToUse = (query ?? q).trim()
    if (!queryToUse) return
    setLoading(true)
    setError(null)
    setResults(null)
    try {
      const url = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/search/semantic?q=${encodeURIComponent(queryToUse)}`
      const res = await fetch(url)
      if (!res.ok) {
        throw new Error(`Search error: ${res.statusText}`)
      }
      const data = await res.json()
      const arr: RecResult[] = data.results ?? []
      setResults(arr)
    } catch (e: any) {
      setError(e.message || 'Search failed')
    } finally {
      setLoading(false)
    }
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

{/* <h2 className="text-base font-semibold text-[rgb(var(--accent))] mb-1">
  Explore popular themes
</h2> */}
<p className="text-sm text-muted mb-3">
  Click a preset to see how semantic search works:
</p>
        <div className="mt-4 flex flex-wrap gap-2">
          {recPresets.map((p) => (
            <Link
              key={p.label}
              href={`/search?q=${encodeURIComponent(p.q)}`}
              className="rounded-full border border-[rgb(var(--accent))]/40 text-[rgb(var(--accent))]
                         px-3 py-1.5 text-xs font-medium bg-[rgb(var(--accent-soft))]/40
                         hover:bg-[rgb(var(--accent-soft))]/70 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-sm"
            >
              {p.label}
            </Link>
          ))}
        </div>

        <div className="flex gap-2">
          <input
            className="border rounded px-3 py-2 w-full focus:outline-none focus:ring-2 focus:ring-[rgb(var(--accent))]/35 focus:border-[rgb(var(--accent))]"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder='e.g. "Victorian social novel", "dystopian novels"'
          />
          <Button size="lg" onClick={() => run()} disabled={!q || loading}>
            {loading ? 'Searching…' : 'Search'}
          </Button>
        </div>

        <BookList<RecResult>
          items={results}
          loading={loading}
          error={error}
          emptyMessage="No results - try adjusting your query."
          metricAccessor={(rec) => (typeof rec.cosine === 'number' ? rec.cosine : undefined)}
          metricLabel="cos"
          variant="default"
          skeletonCount={5}
          onItemClick={(rec) => {
            console.log('clicked rec', rec)
          }}
        />
      </div>
    </PageShell>
  )
}
