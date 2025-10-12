import { Suspense } from 'react'
import RecsClient from './RecsClient'

export default function Page() {
  return (
    <Suspense fallback={<div className="p-6">Loading recommendations…</div>}>
      <RecsClient />
    </Suspense>
  )
}
