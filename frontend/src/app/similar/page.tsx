'use client'

import { useEffect, useRef, useState } from 'react'
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

type SimilarResult = {
  id: number
  title: string
  author?: string | null
  published_year?: number | null
  subtitle?: string | null
  cosine?: number
  reason?: string
  why?: string
  channels?: { cf?: number; semantic?: number }
}

export default function SimilarByTitlePage() {
  const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const [query, setQuery] = useState('')
  const [hits, setHits] = useState<BookHit[]>([])
  const [searching, setSearching] = useState(false)
  const [searchErr, setSearchErr] = useState<string | null>(null)

  const [selected, setSelected] = useState<BookHit | null>(null)
  const [results, setResults] = useState<SimilarResult[] | null>(null)
  const [loadingSimilar, setLoadingSimilar] = useState(false)
  const [similarErr, setSimilarErr] = useState<string | null>(null)

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  // Live search as user types
  useEffect(() => {
    if (!query || query.trim().length < 2) {
      setHits([])
      setSearchErr(null)
      if (abortRef.current) abortRef.current.abort()
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
      if (abortRef.current) abortRef.current.abort()
      const ctrl = new AbortController()
      abortRef.current = ctrl
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
    }, 200)
  }, [query, API])

  async function fetchSimilar(book: BookHit) {
    setSelected(book)
    setResults(null)
    setSimilarErr(null)
    setLoadingSimilar(true)
    try {
      const url = `${API}/books/${encodeURIComponent(String(book.id))}/similar`
      const res = await fetch(url)
      if (!res.ok) {
        const msg = await res.text()
        throw new Error(msg || `HTTP ${res.status}`)
      }
      const data = await res.json()
      const arr: SimilarResult[] = data.results ?? []
      setResults(arr)
    } catch (e: any) {
      setSimilarErr(e.message || 'Failed to fetch similar titles')
    } finally {
      setLoadingSimilar(false)
    }
  }

  function onPick(hit: BookHit) {
    setQuery(`${hit.title}${hit.author ? ` - ${hit.author}` : ''}`)
    setHits([])
    fetchSimilar(hit)
  }

  function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (hits.length > 0) onPick(hits[0])
  }

  return (
    <PageShell>
      <div className="max-w-3xl mx-auto p-6 space-y-6">
        <h1 className="text-2xl font-semibold">Similar Books (by Title)</h1>

        <form onSubmit={onSubmit} className="space-y-3">
          <div className="relative">
            <input
              className="w-full rounded-md border border-[rgb(var(--border-warm))]
                         bg-white/70 dark:bg-black/20 px-3 py-2
                         focus:outline-none focus:ring-2 focus:ring-[rgb(var(--accent))]/35 focus:border-[rgb(var(--accent))]"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Type a title, e.g. “To the Lighthouse”"
              aria-label="Search book title"
              autoComplete="off"
            />
            {searching && (
              <div className="absolute right-2 top-2 text-sm text-muted">Searching…</div>
            )}
          </div>

          {searchErr && <div className="text-sm text-red-600">{searchErr}</div>}

          {(hits.length > 0 || searching) && (
            <BookList<BookHit>
              items={hits}
              loading={searching}
              error={searchErr}
              emptyMessage=""
              metricAccessor={undefined}
              variant="compact"
              skeletonCount={4}
              onItemClick={(hit) => onPick(hit)}
            />
          )}

          <div className="flex items-center gap-3">
            <Button
              size="lg"
              type="submit"
              disabled={searching || (hits.length === 0 && !selected)}
              title="Press Enter to select top suggestion"
            >
              Find Similar
            </Button>
            {selected && (
              <span className="text-sm text-muted">
                Selected: <strong className="text-[rgb(var(--foreground))]">{selected.title}</strong>
                {selected.author ? ` – ${selected.author}` : ''}
              </span>
            )}
          </div>
        </form>

        <BookList<SimilarResult>
          items={results}
          loading={loadingSimilar}
          error={similarErr}
          emptyMessage="No similar titles found for this selection - try another book."
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
