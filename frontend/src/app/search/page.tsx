import { Suspense } from 'react'
import SearchClient from './SearchClient'

export default function Page() {
  return (
    <Suspense fallback={<div className="p-6">Loading search…</div>}>
      <SearchClient />
    </Suspense>
  )
}
