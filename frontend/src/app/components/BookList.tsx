'use client'
import React from 'react'

export type BookListItem = {
  id: number | string
  title?: string
  author?: string | null
  published_year?: number | null
  subtitle?: string | null
}

type Props<T extends BookListItem> = {
  items: T[] | null
  loading?: boolean
  error?: string | null
  emptyMessage?: string
  onItemClick?: (item: T) => void
  metricAccessor?: (item: T) => number | undefined
  metricLabel?: string
  variant?: 'default' | 'compact'
  skeletonCount?: number
  renderFooter?: (item: T) => React.ReactNode
}

export default function BookList<T extends BookListItem>({
  items,
  loading = false,
  error = null,
  emptyMessage = 'No results',
  onItemClick,
  metricAccessor,
  metricLabel = 'cos',
  variant = 'default',
  skeletonCount = 5,
  renderFooter,
}: Props<T>) {
  if (error) {
    return <div className="text-sm text-red-600">{error}</div>
  }
  if (loading) {
    return (
      <ul className="space-y-2">
        {Array.from({ length: skeletonCount }).map((_, i) => (
          <li key={i} className={containerClass(variant) + ' animate-pulse'}>
            <div className="flex-1 space-y-2">
              <div className="h-4 w-1/2 rounded bg-[rgb(var(--accent-soft))]/50" />
              <div className="h-3 w-1/3 rounded bg-[rgb(var(--accent-soft))]/40" />
            </div>
          </li>
        ))}
      </ul>
    )
  }
  if (!items || items.length === 0) {
    return (
      <div className="rounded-xl border border-[rgb(var(--border-warm))] p-6 surface-tinted">
        <div className="text-sm text-muted">{emptyMessage}</div>
      </div>
    )
  }

  return (
    <ul
      className={
        variant === 'compact'
          ? 'rounded-xl border border-[rgb(var(--border-warm))] divide-y bg-white/70 dark:bg:black/20 overflow-hidden'
          : 'grid grid-cols-1 gap-2'
      }
    >
      {items.map((r) => {
        const metricVal = metricAccessor ? metricAccessor(r) : undefined
        return (
          <li
            key={r.id}
            className={containerClass(variant)}
            onClick={onItemClick ? () => onItemClick(r) : undefined}
            role={onItemClick ? 'button' : undefined}
            tabIndex={onItemClick ? 0 : undefined}
            onKeyDown={
              onItemClick
                ? (e: React.KeyboardEvent<HTMLLIElement>) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      onItemClick(r)
                    }
                  }
                : undefined
            }
          >
            <div className="min-w-0 flex-1">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="font-medium truncate">
                    {r.title ?? '(Untitled)'}
                    {r.subtitle ? <span className="opacity-70">: {r.subtitle}</span> : null}
                  </div>
                  <div className="text-sm text-muted">
                    {r.author ? `by ${r.author}` : ''}
                    {r.published_year ? (r.author ? ` · ${r.published_year}` : r.published_year) : ''}
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {typeof metricVal === 'number' && (
                    <span className="text-xs rounded-full border px-2 py-0.5 border-[rgb(var(--accent))]/40 text-[rgb(var(--accent))]">
                      {metricLabel} {metricVal.toFixed(3)}
                    </span>
                  )}
                  {r.published_year && variant === 'default' && (
                    <span className="text-xs rounded-full border px-2 py-0.5 border-[rgb(var(--border-warm))] text-muted">
                      {r.published_year}
                    </span>
                  )}
                </div>
              </div>

              {renderFooter && <div className="mt-2 text-sm">{renderFooter(r)}</div>}
            </div>
          </li>
        )
      })}
    </ul>
  )
}

function containerClass(variant: 'default' | 'compact') {
  if (variant === 'compact') {
    return 'p-3 cursor-pointer transition-all hover:bg-[rgb(var(--accent-soft))]/40 focus-within:bg-[rgb(var(--accent-soft))]/40'
  }
  return 'group rounded-xl border border-[rgb(var(--border-warm))] p-4 bg-white/70 dark:bg-black/20 hover:-translate-y-0.5 hover:shadow-sm transition-all duration-200 focus-within:ring-2 focus-within:ring-[rgb(var(--accent))]/30'
}
