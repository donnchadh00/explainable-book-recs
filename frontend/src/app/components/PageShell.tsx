'use client'

import Topbar from "./Topbar";

export default function PageShell({
  children,
  bg = "bg-[rgb(var(--background))]",
}: {
  children: React.ReactNode;
  bg?: string;
}) {
  return (
    <div className={`${bg} min-h-screen text-[rgb(var(--foreground))]`}>
      <Topbar />
      <main className="mx-auto max-w-5xl px-6 pt-16 pb-16 sm:pt-20">
        {children}
      </main>
      <footer className="border-t border-[rgb(var(--border-warm))]">
        <div className="mx-auto max-w-5xl px-6 py-6 text-sm text-muted">
          Built with Next.js · FastAPI · Postgres/pgvector
        </div>
      </footer>
    </div>
  );
}
