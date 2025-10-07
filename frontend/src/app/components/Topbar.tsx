'use client'

import Link from "next/link";

export default function Topbar() {
  return (
    <header className="border-b border-black/10 dark:border-white/10">
      <div className="mx-auto max-w-5xl px-6 py-6 flex items-center justify-between">
        <div className="flex items-baseline gap-2">
          <Link
            href="/"
            className="text-xl font-bold tracking-tight hover:opacity-80 transition-opacity"
            aria-label="Go to homepage"
          >
            Book Recommender
          </Link>
        </div>
        <nav className="hidden sm:flex gap-4 text-sm">
          <Link href="/recs" className="hover:underline">Recommendations</Link>
          <Link href="/search" className="hover:underline">Semantic Search</Link>
          <Link href="/similar" className="hover:underline">Similar Books</Link>
        </nav>
      </div>
    </header>
  );
}
