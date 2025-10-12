import { Suspense } from 'react'
import SimilarClient from './SimilarClient'

export default function Page() {
  return (
    <Suspense fallback={<div className="p-6">Loading similar books…</div>}>
      <SimilarClient />
    </Suspense>
  )
}
