'use client'
import { useState } from 'react'

export default function SemanticSearchPage() {
    const [q, setQ] = useState('')
    const [results, setResults] = useState<any[] | null>(null)
    const [loading, setLoading] = useState(false)

    async function run() {
        setLoading(true)
        setResults(null)
        const url = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/search/semantic?q=${encodeURIComponent(q)}`
        const res = await fetch(url)
        const data = await res.json()
        setResults(data.results)
        setLoading(false)
    }

    return (
        <div className="max-w-3xl mx-auto p-6 space-y-4">
            <h1 className="text-2xl font-semibold">Semantic Search</h1>
            <div className="flex gap-2">
                <input className="border rounded px-3 py-2 w-full" value={q} onChange={e=>setQ(e.target.value)} placeholder="Try 'western horror'"/>
                <button onClick={run} className="px-4 py-2 rounded bg-black text-white disabled:opacity-50" disabled={!q || loading}>{loading? 'Searching…' : 'Search'}</button>
            </div>
            {results && (
                <ul className="divide-y border rounded">
                    {results.map((r) => (
                        <li key={r.id} className="p-3">
                            <div className="font-medium">{r.title}{r.subtitle ? `: ${r.subtitle}` : ''}</div>
                            <div className="text-sm opacity-70">Cosine ~ {r.cosine?.toFixed(3)}</div>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    )
}
