'use client'

import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import PageShell from "../components/PageShell"

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

  // Free-text semantic query
  const [q, setQ] = useState('')

  // Live search (title/author)
  const [query, setQuery] = useState('')
  const [hits, setHits] = useState<BookHit[]>([])
  const [searching, setSearching] = useState(false)
  const [searchErr, setSearchErr] = useState<string | null>(null)
  const [selected, setSelected] = useState<BookHit | null>(null)

  // Recommendations
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [results, setResults] = useState<Rec[] | null>(null)

  // infra
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const abortSearchRef = useRef<AbortController | null>(null)

  useEffect(() => {
      const qp = searchParams.get('q')
      const seedId = searchParams.get('seed_book_id')
      if (qp && !q) setQ(qp)
    }, [searchParams])

  // live search titles/authors
  useEffect(() => {
    if (!query || query.trim().length < 2) {
      setHits([])
      setSearchErr(null)
      if (abortSearchRef.current) abortSearchRef.current.abort()
      if (debounceRef.current) clearTimeout(debounceRef.current)
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
        const url = `${API}/books/search?q=${encodeURIComponent(query)}`
        const res = await fetch(url, { signal: ctrl.signal })
        if (!res.ok) throw new Error(`Search failed (HTTP ${res.status})`)
        const data = await res.json()
        const arr: BookHit[] = Array.isArray(data) ? data : data.results ?? []
        setHits(arr.slice(0, 10))
      } catch (e: any) {
        if (e.name !== 'AbortError') setSearchErr(e.message || 'Search failed')
      } finally {
        setSearching(false)
      }
    }, 200) // debounce
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

  async function run() {
    setLoading(true)
    setError(null)
    setResults(null)

    try {
      const params = new URLSearchParams()
      if (q) params.set('q', q)
      if (selected?.id) params.set('seed_book_id', String(selected.id))
      params.set('k', '12')

      // timeout + abort
      const ctrl = new AbortController()
      const timeout = setTimeout(() => ctrl.abort(), 12000)
      const res = await fetch(`${API}/recommend?${params.toString()}`, { signal: ctrl.signal })
      clearTimeout(timeout)

      if (!res.ok) {
        const msg = await res.text().catch(() => '')
        throw new Error(msg || `HTTP ${res.status}`)
      }
      const data = await res.json()
      const arr: Rec[] = data.results ?? []
      setResults(arr)
    } catch (e: any) {
      setError(e.name === 'AbortError' ? 'Request timed out. Please try again.' : (e.message || 'Failed to fetch recommendations'))
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
      <h1 className="text-2xl font-semibold">Recommendations</h1>

      {/* Inputs */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Free-text query */}
        <div className="space-y-2">
          <label className="text-sm font-medium">Describe what you want</label>
          <input
            className="border rounded px-3 py-2 w-full"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder='e.g. "Victorian social novel", "dystopian novels"'
          />
          <p className="text-xs opacity-70">Uses semantic matching over embeddings.</p>
        </div>

        {/* Live title/author search */}
        <div className="space-y-2">
          <label className="text-sm font-medium">Pick a seed book (title/author)</label>
          <div className="relative">
            <input
              className="border rounded px-3 py-2 w-full"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Type a title or author…"
              aria-label="Search book by title or author"
            />
            {(searching) && <div className="absolute right-2 top-2 text-xs opacity-60">Searching…</div>}
          </div>

          {searchErr && <div className="text-sm text-red-600">{searchErr}</div>}

          {hits.length > 0 && (
            <ul className="border rounded divide-y max-h-72 overflow-auto">
              {hits.map((h) => (
                <li
                  key={h.id}
                  className="p-3 hover:bg-gray-50 cursor-pointer"
                  onClick={() => pick(h)}
                >
                  <div className="font-medium">
                    {h.title}{h.subtitle ? `: ${h.subtitle}` : ''}
                  </div>
                  <div className="text-sm opacity-70">
                    {h.author ? `${h.author} · ` : ''}{h.published_year ?? ''}
                  </div>
                </li>
              ))}
            </ul>
          )}

          {selected && (
            <div className="flex items-center gap-2 text-sm">
              <span className="opacity-80">Selected:</span>
              <span className="font-medium">
                {selected.title}{selected.author ? ` - ${selected.author}` : ''}
              </span>
              <button onClick={clearSeed} className="ml-2 rounded border px-2 py-0.5 hover:bg-black/5 dark:hover:bg-white/10">
                Change
              </button>
            </div>
          )}
        </div>
      </section>

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={run}
          className="px-4 py-2 rounded bg-black text-white disabled:opacity-50"
          disabled={loading || (!q && !selected)}
        >
          {loading ? 'Finding…' : 'Get recommendations'}
        </button>
        <button onClick={resetAll} className="px-4 py-2 rounded border">
          Reset
        </button>
      </div>

      {/* Results */}
      {error && <div className="text-sm text-red-600">{error}</div>}

      {results && (
        <ul className="border rounded divide-y">
          {results.map((r) => (
            <li key={r.id} className="p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="font-medium">
                    {r.title}
                  </div>
                  <div className="text-sm opacity-70">
                    {r.author ? `by ${r.author}` : ''}
                    {r.published_year ? (r.author ? ` · ${r.published_year}` : r.published_year) : ''}
                  </div>
                </div>
                <div className="text-sm opacity-70 whitespace-nowrap self-center">
                  {typeof r.score === 'number' ? `Score ${r.score.toFixed(3)}` : ''}
                </div>
              </div>
              {/* reason/why */}
              {(r.reason || r.why) && (
                <div className="mt-2 text-sm opacity-90">
                  {r.reason ?? r.why}
                </div>
              )}
              {/* channel badges */}
              {r.channels && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {typeof r.channels.semantic === 'number' && (
                    <span className="text-xs rounded-full border px-2 py-0.5">
                      semantic {r.channels.semantic.toFixed(2)}
                    </span>
                  )}
                  {typeof r.channels.cf === 'number' && (
                    <span className="text-xs rounded-full border px-2 py-0.5">
                      cf {r.channels.cf.toFixed(2)}
                    </span>
                  )}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </PageShell>
  )
}
