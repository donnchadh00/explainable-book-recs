import Link from "next/link";

function Card({
  title,
  href,
  desc,
}: {
  title: string;
  href: string;
  desc: string;
}) {
  return (
    <Link
      href={href}
      className="group block rounded-2xl border border-black/10 dark:border-white/10 p-5 hover:shadow-md transition-shadow focus:outline-none focus:ring-2 focus:ring-black/30 dark:focus:ring-white/30"
    >
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">{title}</h3>
        <span
          aria-hidden
          className="translate-x-0 group-hover:translate-x-0.5 transition-transform"
        >
          →
        </span>
      </div>
      <p className="mt-1 text-sm text-black/60 dark:text-white/60">{desc}</p>
    </Link>
  );
}

export default function Home() {
  return (
    <div className="min-h-screen bg-white dark:bg-black text-black dark:text-white">
      <header className="border-b border-black/10 dark:border-white/10">
        <div className="mx-auto max-w-5xl px-6 py-6 flex items-center justify-between">
          <div className="flex items-baseline gap-2">
            <span className="text-xl font-bold tracking-tight">Book Recommender</span>
          </div>
          <nav className="hidden sm:flex gap-4 text-sm">
            <Link href="/search" className="hover:underline">
              Semantic Search
            </Link>
            <Link href="/similar" className="hover:underline">
              Similar Books
            </Link>
            <Link href="/recs" className="hover:underline">
              Recommendations
            </Link>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6">
        {/* Hero */}
        <section className="py-12 sm:py-16">
          <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight">
            Find your next great read.
          </h1>
          <p className="mt-3 text-black/70 dark:text-white/70 max-w-2xl">
            Explore books with semantic search, discover lookalikes with vector
            similarity, or get personalized picks with collaborative
            filtering (coming soon).
          </p>

          <div className="mt-6 flex flex-col sm:flex-row gap-3">
            <Link
              href="/search"
              className="inline-flex items-center justify-center rounded-xl px-4 py-2.5 text-sm font-medium bg-black text-white dark:bg-white dark:text-black hover:opacity-90 transition-opacity"
            >
              Try Semantic Search
            </Link>
            <Link
              href="/similar"
              className="inline-flex items-center justify-center rounded-xl px-4 py-2.5 text-sm font-medium border border-black/10 dark:border-white/15 hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
            >
              Find Similar Books
            </Link>
          </div>
        </section>

        {/* Feature cards */}
        <section className="pb-20">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <Card
              title="Semantic Search"
              href="/search"
              desc="Describe a vibe or theme (e.g. “existential satire”) and search across embeddings."
            />
            <Card
              title="Similar Books"
              href="/similar"
              desc="Pick a title and see vector-nearest neighbors ranked by cosine similarity."
            />
            <Card
              title="Recommendations"
              href="/recs"
              desc="Health check + sample data today; personalized hybrid recs coming next."
            />
          </div>
        </section>
      </main>

      <footer className="border-t border-black/10 dark:border-white/10">
        <div className="mx-auto max-w-5xl px-6 py-6 text-sm text-black/60 dark:text-white/60">
          Built with Next.js · FastAPI · Postgres/pgvector
        </div>
      </footer>
    </div>
  );
}
