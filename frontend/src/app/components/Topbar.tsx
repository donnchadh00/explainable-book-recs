'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

const NAV = [
  { href: '/recs',   label: 'Recommendations' },
  { href: '/search', label: 'Semantic Search' },
  { href: '/similar',label: 'Similar Books' },
]

export default function Topbar() {
  const pathname = usePathname()

  return (
    <header
      className="sticky top-0 z-50
                 bg-[rgb(var(--background))]/80
                 backdrop-blur-md supports-[backdrop-filter]:backdrop-blur-md
                 border-b border-[rgb(var(--border-warm))]
                 shadow-[0_2px_12px_rgba(0,0,0,0.08)] dark:shadow-[0_2px_12px_rgba(0,0,0,0.35)]"
    >
      {/* subtle top gradient sheen */}
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-white/10 to-transparent dark:from-white/5" />

      <div className="relative mx-auto max-w-5xl px-6 h-16 flex items-center justify-between">
        {/* Brand */}
        <Link
          href="/"
          className="text-[rgb(var(--accent))] hover:opacity-90 transition-opacity
                     text-xl font-semibold tracking-tight"
          aria-label="Go to homepage"
        >
          Book Recommender
        </Link>

        {/* Nav */}
        <nav className="hidden sm:flex items-center gap-6 text-sm font-medium">
          {NAV.map(({ href, label }) => {
            const active = pathname === href
            return (
              <Link
                key={href}
                href={href}
                className={`relative transition-colors duration-200 group
                            ${active ? 'text-[rgb(var(--accent))]' : 'text-[rgb(var(--foreground))]/80 hover:text-[rgb(var(--accent))]'}
                           `}
              >
                {label}
                {/* animated underline */}
                <span
                  className={`absolute left-0 -bottom-1 h-[2px] rounded-full
                              bg-[rgb(var(--accent))]
                              transition-all duration-300 ease-out
                              ${active ? 'w-full' : 'w-0 group-hover:w-full'}`}
                />
              </Link>
            )
          })}
        </nav>
      </div>
    </header>
  )
}
