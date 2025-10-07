'use client'

import Topbar from "./Topbar";

export default function PageShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-white dark:bg-black text-black dark:text-white">
      <Topbar />
      <main className="mx-auto max-w-5xl px-6 py-12 sm:py-16">{children}</main>
      <footer className="border-t border-black/10 dark:border-white/10">
        <div className="mx-auto max-w-5xl px-6 py-6 text-sm text-black/60 dark:text-white/60">
          Built with Next.js · FastAPI · Postgres/pgvector
        </div>
      </footer>
    </div>
  );
}
