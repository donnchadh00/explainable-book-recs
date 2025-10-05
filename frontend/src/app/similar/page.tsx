'use client'

import { useEffect, useRef, useState } from 'react'

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

  // Live search titles as the user types
  useEffect(() => {
    if (!query || query.trim().length < 2) {
      setHits([])
      setSearchErr(null)
      if (abortRef.current) abortRef.current.abort()
      if (debounceRef.current) clearTimeout(debounceRef.current)
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
        // Expecting either {results:[...]} or [...]
        const arr: BookHit[] = Array.isArray(data) ? data : data.results ?? []
        setHits(arr.slice(0, 10))
      } catch (e: any) {
        if (e.name !== 'AbortError') setSearchErr(e.message || 'Search failed')
      } finally {
        setSearching(false)
      }
    }, 200) // simple debounce
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
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Similar Books (by Title)</h1>

      <form onSubmit={onSubmit} className="space-y-2">
        <div className="relative">
          <input
            className="border rounded px-3 py-2 w-full"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type a title, e.g. “To the Lighthouse”"
            aria-label="Search book title"
          />
          {searching && (
            <div className="absolute right-2 top-2 text-sm opacity-60">Searching…</div>
          )}
        </div>

        {searchErr && <div className="text-sm text-red-600">{searchErr}</div>}

        {hits.length > 0 && (
          <ul className="border rounded divide-y">
            {hits.map((h) => (
              <li key={h.id} className="p-3 hover:bg-gray-50 cursor-pointer" onClick={() => onPick(h)}>
                <div className="font-medium">
                  {h.title}{h.subtitle ? `: ${h.subtitle}` : ''}
                </div>
                <div className="text-sm opacity-70">
                  {h.author ? `${h.author} · ` : ''}
                  {h.published_year ?? ''}
                </div>
              </li>
            ))}
          </ul>
        )}

        <div className="flex gap-2">
          <button
            type="submit"
            className="px-4 py-2 rounded bg-black text-white disabled:opacity-50"
            disabled={searching || (hits.length === 0 && !selected)}
            title="Press Enter to use the top suggestion"
          >
            Find Similar
          </button>
          {selected && (
            <span className="text-sm opacity-70 self-center">
              Selected: <strong>{selected.title}</strong>
              {selected.author ? ` - ${selected.author}` : ''}
            </span>
          )}
        </div>
      </form>

      {similarErr && <div className="text-sm text-red-600">{similarErr}</div>}

      {loadingSimilar && <div>Loading similar titles…</div>}

      {results && (
        <ul className="divide-y border rounded">
          {results.map((r) => (
            <li key={r.id} className="p-3">
              <div className="font-medium">
                {r.title}{r.subtitle ? `: ${r.subtitle}` : ''}
              </div>
              <div className="text-sm opacity-70">
                {r.author ? `by ${r.author} · ` : ''}
                {r.published_year ? `${r.published_year} · ` : ''}
                Cosine ~ {typeof r.cosine === 'number' ? r.cosine.toFixed(3) : r.cosine}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
