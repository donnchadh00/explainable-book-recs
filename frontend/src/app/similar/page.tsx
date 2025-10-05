'use client'

import { useState } from 'react'

export default function SimilarBooksPage() {
  const [bookId, setBookId] = useState('')
  const [results, setResults] = useState<any[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function run() {
    if (!bookId) return
    setLoading(true)
    setError(null)
    setResults(null)

    try {
      const url = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/books/${encodeURIComponent(bookId)}/similar`
      const res = await fetch(url)
      if (!res.ok) {
        const msg = await res.text()
        throw new Error(msg || `HTTP ${res.status}`)
      }
      const data = await res.json()
      setResults(data.results)
    } catch (err: any) {
      setError(err.message || 'Failed to fetch')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-4">
      <h1 className="text-2xl font-semibold">Similar Books</h1>

      <div className="flex gap-2">
        <input
          className="border rounded px-3 py-2 w-full"
          value={bookId}
          onChange={(e) => setBookId(e.target.value)}
          placeholder="Enter a book ID (e.g. 1234)"
        />
        <button
          onClick={run}
          className="px-4 py-2 rounded bg-black text-white disabled:opacity-50"
          disabled={!bookId || loading}
        >
          {loading ? 'Loading…' : 'Find'}
        </button>
      </div>

      {error && <div className="text-red-600 text-sm">{error}</div>}

      {results && (
        <ul className="divide-y border rounded">
          {results.map((r) => (
            <li key={r.id} className="p-3">
              <div className="font-medium">
                {r.title}
                {r.subtitle ? `: ${r.subtitle}` : ''}
              </div>
              <div className="text-sm opacity-70">
                {r.published_year ? `${r.published_year} · ` : ''}
                Cosine ~ {r.cosine?.toFixed(3)}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
