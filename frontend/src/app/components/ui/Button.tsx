'use client'
import React from 'react'

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'outline' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
}

const base =
  'inline-flex items-center justify-center rounded-md font-medium transition-colors ' +
  'focus:outline-none focus-visible:ring-2 focus-visible:ring-[rgb(var(--accent))]/40 disabled:opacity-50 disabled:pointer-events-none'

const variants: Record<NonNullable<ButtonProps['variant']>, string> = {
  primary:
    'bg-[rgb(var(--accent))] text-white hover:bg-[rgb(var(--accent-hover))]',
  outline:
    'border border-[rgb(var(--accent))] text-[rgb(var(--accent))] hover:bg-[rgb(var(--accent))]/10',
  ghost:
    'text-[rgb(var(--accent))] hover:bg-[rgb(var(--accent))]/10'
}

const sizes: Record<NonNullable<ButtonProps['size']>, string> = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-sm',
  lg: 'px-5 py-2.5 text-base'
}

export default function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  className,
  children,
  ...props
}: ButtonProps) {
  const extra = className || ''
  return (
    <button
      className={`${base} ${variants[variant]} ${sizes[size]} ${extra}`}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading && (
        <span className="mr-2 inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/70 border-t-transparent" />
      )}
      {children}
    </button>
  )
}
