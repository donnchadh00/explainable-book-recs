'use client'

import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import PageShell from '../components/PageShell'
import Button from '../components/ui/Button'
import BookList from '../components/BookList'

type BookHit = {
  id: number
  title: string
  author?: string | null
  published_year?: number | null
  subtitle?: string | null
}

type Rec = {
  id: number
  title?: string
  author?: string | null
  published_year?: number | null
  score?: number
  channels?: { cf?: number; semantic?: number }
  reason?: string
  why?: string
}

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function RecsPage() {
  const searchParams = useSearchParams()

  const [q, setQ] = useState('')
  const [query, setQuery] = useState('')
  const [hits, setHits] = useState<BookHit[]>([])
  const [searching, setSearching] = useState(false)
  const [searchErr, setSearchErr] = useState<string | null>(null)
  const [selected, setSelected] = useState<BookHit | null>(null)

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [results, setResults] = useState<Rec[] | null>(null)

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const abortSearchRef = useRef<AbortController | null>(null)

  // preload from query param
  useEffect(() => {
    const qp = searchParams.get('q')
    if (qp && !q) {
      setQ(qp)
      run(qp)
    }
  }, [searchParams])

  // live title/author search
  useEffect(() => {
    if (!query || query.trim().length < 2) {
      setHits([])
      setSearchErr(null)
      if (abortSearchRef.current) abortSearchRef.current.abort()
      if (debounceRef.current) clearTimeout(debounceRef.current)
      setHits([]);
      setSearchErr(null);
      setSearching(false);
      return
    }

    setSearching(true)
    setSearchErr(null)

    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(async () => {
      if (abortSearchRef.current) abortSearchRef.current.abort()
      const ctrl = new AbortController()
      abortSearchRef.current = ctrl
      try {
        const res = await fetch(`${API}/books/search?q=${encodeURIComponent(query)}`, { signal: ctrl.signal })
        if (!res.ok) throw new Error(`Search failed (${res.status})`)
        const data = await res.json()
        const arr: BookHit[] = Array.isArray(data) ? data : data.results ?? []
        setHits(arr.slice(0, 10))
      } catch (e: any) {
        if (e.name !== 'AbortError') setSearchErr(e.message || 'Search failed')
      } finally {
        setSearching(false)
      }
    }, 200)
  }, [query])

  function pick(hit: BookHit) {
    setSelected(hit)
    setQuery(`${hit.title}${hit.author ? ` - ${hit.author}` : ''}`)
    setHits([])
  }

  function clearSeed() {
    setSelected(null)
    setQuery('')
    setHits([])
  }

  async function run(queryOverride?: string) {
    const queryText = queryOverride ?? q
    if (!queryText && !selected) return

    setLoading(true)
    setError(null)
    setResults(null)

    try {
      const params = new URLSearchParams()
      if (queryText) params.set('q', queryText)
      if (selected?.id) params.set('seed_book_id', String(selected.id))
      params.set('k', '12')

      const ctrl = new AbortController()
      const timeout = setTimeout(() => ctrl.abort(), 12000)
      const res = await fetch(`${API}/recommend?${params.toString()}`, { signal: ctrl.signal })
      clearTimeout(timeout)

      if (!res.ok) throw new Error(await res.text() || `HTTP ${res.status}`)

      const data = await res.json()
      setResults(data.results ?? [])
    } catch (e: any) {
      setError(e.name === 'AbortError' ? 'Request timed out - please try again.' : e.message || 'Failed to fetch recommendations')
    } finally {
      setLoading(false)
    }
  }

  function resetAll() {
    setQ('')
    clearSeed()
    setResults(null)
    setError(null)
  }

  return (
    <PageShell>
      <div className="max-w-5xl mx-auto p-6 space-y-5">
        <h1 className="text-2xl font-semibold">Recommendations</h1>

        {/* Inputs */}
        <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-2">
            <label className="text-sm font-medium">Describe what you want</label>
            <input
              className="border border-[rgb(var(--border-warm))] rounded px-3 py-2 w-full
                         bg-white/70 dark:bg-black/20
                         focus:outline-none focus:ring-2 focus:ring-[rgb(var(--accent))]/35"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder='e.g. "Victorian social novel", "dystopian novels"'
            />
            <p className="text-xs text-muted">Uses semantic matching over embeddings.</p>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Pick a seed book (title/author)</label>
            <div className="relative">
              <input
                className="border border-[rgb(var(--border-warm))] rounded px-3 py-2 w-full
                           bg-white/70 dark:bg-black/20
                           focus:outline-none focus:ring-2 focus:ring-[rgb(var(--accent))]/35"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Type a title or author…"
                aria-label="Search book by title or author"
              />
              {searching && (
                <div className="absolute right-2 top-2 text-xs text-muted">Searching…</div>
              )}
            </div>

            {(hits.length > 0 || searching) && (
              <BookList<BookHit>
                items={hits}
                loading={searching}
                error={searchErr}
                emptyMessage=""
                metricAccessor={undefined}
                variant="compact"
                skeletonCount={4}
                onItemClick={(hit) => pick(hit)}
              />
            )}

            {selected && (
              <div className="flex items-center gap-2 text-sm">
                <span className="opacity-80">Selected:</span>
                <span className="font-medium">
                  {selected.title}{selected.author ? ` - ${selected.author}` : ''}
                </span>
                <button
                  onClick={clearSeed}
                  className="ml-2 rounded border px-2 py-0.5 hover:bg-[rgb(var(--accent-soft))]/30 transition"
                >
                  Change
                </button>
              </div>
            )}
          </div>
        </section>

        {/* Actions */}
        <div className="flex gap-2">
          <Button size="lg" onClick={() => run()} disabled={loading || (!q && !selected)}>
            {loading ? 'Finding…' : 'Get recommendations'}
          </Button>
          <Button size="lg" variant="outline" onClick={resetAll}>Reset</Button>
        </div>

        {/* Results */}
        <BookList<Rec>
          items={results}
          loading={loading}
          error={error}
          emptyMessage="No recommendations yet - try a different description or seed book."
          metricAccessor={(r) => (typeof r.score === 'number' ? r.score : undefined)}
          metricLabel="score"
          variant="default"
          skeletonCount={6}
          onItemClick={(r) => {
            console.log('clicked rec', r)
          }}
          renderFooter={(r) => (
            <>
              {(r.reason || r.why) && <p className="opacity-90">{r.reason ?? r.why}</p>}
              {r.channels && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {typeof r.channels.semantic === 'number' && (
                    <span className="text-xs rounded-full border px-2 py-0.5 border-[rgb(var(--accent))]/40 text-[rgb(var(--accent))]">
                      semantic {r.channels.semantic.toFixed(2)}
                    </span>
                  )}
                  {typeof r.channels.cf === 'number' && (
                    <span className="text-xs rounded-full border px-2 py-0.5 border-[rgb(var(--border-warm))] text-muted">
                      cf {r.channels.cf.toFixed(2)}
                    </span>
                  )}
                </div>
              )}
            </>
          )}
        />
      </div>
    </PageShell>
  )
}
