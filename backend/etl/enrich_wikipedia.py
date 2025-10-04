from __future__ import annotations
import argparse
import asyncio
import html
import os
from typing import List, Optional, Tuple

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from app.db import SessionLocal
from app.models.book import Book


WIKI_API = "https://en.wikipedia.org/w/api.php"


# Wikipedia helpers (async)

async def _fetch_json(client: httpx.AsyncClient, params: dict, retries: int = 3) -> dict:
    """Generic GET to enwiki Action API with simple retry."""
    last: Optional[Exception] = None
    for attempt in range(retries):
        try:
            r = await client.get(WIKI_API, params=params, timeout=30)
            # Simple backoff on transient server issues
            if r.status_code in (429, 500, 502, 503, 504):
                await asyncio.sleep(0.5 * (2 ** attempt))
                continue
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last = e
            await asyncio.sleep(0.5 * (2 ** attempt))
    raise last or RuntimeError("Wikipedia API request failed")


async def wiki_search_best_pageid(
    client: httpx.AsyncClient, title: str, author: Optional[str]
) -> Optional[int]:
    """
    Use enwiki 'search' to find best page for "title [author]".
    Returns pageid or None.
    """
    if not title:
        return None

    query = title
    if author and author.strip():
        query = f"{title} {author}"

    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": 1,
        "srinfo": "suggestion",
        "format": "json",
        "utf8": 1,
        "origin": "*",
    }
    data = await _fetch_json(client, params)
    hits = (data.get("query") or {}).get("search") or []
    if not hits:
        # fall back to title only if author search failed
        if author:
            params["srsearch"] = title
            data = await _fetch_json(client, params)
            hits = (data.get("query") or {}).get("search") or []
            if not hits:
                return None
        else:
            return None

    pageid = hits[0].get("pageid")
    return int(pageid) if pageid is not None else None


async def wiki_get_full_plaintext_by_pageid(
    client: httpx.AsyncClient, pageid: int
) -> Optional[str]:
    """
    Get the **full** plain-text extract of a page (not just the lead).
    Uses action=query&prop=extracts with explaintext=1.
    """
    params = {
        "action": "query",
        "prop": "extracts",
        "explaintext": 1,            # plain text (no HTML)
        "exsectionformat": "plain",  # simpler section headings
        "pageids": str(pageid),
        "format": "json",
        "utf8": 1,
        "origin": "*",
    }
    data = await _fetch_json(client, params)
    pages = (data.get("query") or {}).get("pages") or {}
    page = next(iter(pages.values()), None)
    if not page:
        return None
    extract = page.get("extract")
    if not extract:
        return None
    # Ensure plain unicode string
    return html.unescape(extract).strip() or None


# DB candidate selection

def candidate_books(db: Session, min_chars: int, limit: Optional[int]) -> List[Tuple[int, str, Optional[str]]]:
    """
    Return books that need enrichment:
      - description IS NULL OR length(description) < min_chars
    """
    total = db.execute(text("SELECT COUNT(*) FROM books")).scalar()
    eligible = db.execute(
        text("SELECT COUNT(*) FROM books WHERE description IS NULL OR length(description) < :m"),
        {"m": min_chars},
    ).scalar()
    print(f"[wiki] books total={total}, eligible(<{min_chars})={eligible}")

    sql = """
      SELECT id, title, author
      FROM books
      WHERE description IS NULL OR length(description) < :m
      ORDER BY id
    """
    params = {"m": min_chars}
    if limit:
        sql += " LIMIT :limit"
        params["limit"] = limit

    rows = db.execute(text(sql), params).all()
    # Return lightweight tuples to avoid ORM overhead
    return [(int(r[0]), str(r[1]), (r[2] if r[2] is not None else None)) for r in rows]


# Main routine

async def enrich_with_wikipedia(
    min_chars: int,
    limit: Optional[int],
    concurrency: int,
    batch_commit: int,
    dry_run: bool,
):
    updated = 0
    skipped = 0
    errors = 0

    books: List[Tuple[int, str, Optional[str]]]
    with SessionLocal() as db:
        books = candidate_books(db, min_chars=min_chars, limit=limit)

    if not books:
        print("Wikipedia enrich complete — candidates: 0, updated: 0, skipped: 0")
        return

    limits = httpx.Limits(max_keepalive_connections=concurrency, max_connections=concurrency * 2)
    async with httpx.AsyncClient(http2=True, timeout=30, limits=limits, headers={"User-Agent": "book-recs/wiki-enrich"}) as client:
        sem = asyncio.Semaphore(concurrency)

        # Keep a DB session for batching updates efficiently
        with SessionLocal() as db:
            pending = 0

            async def process_one(bid: int, title: str, author: Optional[str]):
                nonlocal updated, skipped, errors, pending
                async with sem:
                    try:
                        pageid = await wiki_search_best_pageid(client, title, author)
                        if not pageid:
                            skipped += 1
                            return

                        full_text = await wiki_get_full_plaintext_by_pageid(client, pageid)
                        if not full_text:
                            skipped += 1
                            return

                        # Replace description with full Wikipedia article text
                        if dry_run:
                            # just count as updated, do not write
                            updated += 1
                            return

                        db.execute(
                            text("UPDATE books SET description = :d WHERE id = :id"),
                            {"d": full_text, "id": bid},
                        )
                        pending += 1
                        updated += 1

                        if pending >= batch_commit:
                            db.commit()
                            pending = 0
                    except Exception:
                        errors += 1

            # Dispatch tasks
            tasks: List[asyncio.Task] = []
            for (bid, title, author) in books:
                tasks.append(asyncio.create_task(process_one(bid, title, author)))
            if tasks:
                await asyncio.gather(*tasks)

            # final commit
            if not dry_run and pending > 0:
                db.commit()

    print(f"Wikipedia enrich complete — candidates: {len(books)}, updated: {updated}, skipped: {skipped}, errors: {errors}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-chars", type=int, default=600, help="Books with description shorter than this (or NULL) will be enriched.")
    ap.add_argument("--limit", type=int, default=None, help="Max number of books to process (for testing).")
    ap.add_argument("--concurrency", type=int, default=24, help="Parallel Wikipedia calls.")
    ap.add_argument("--batch-commit", type=int, default=200, help="Commit DB every N updates.")
    ap.add_argument("--dry-run", action="store_true", help="Fetch & count but do not write to DB.")
    args = ap.parse_args()

    asyncio.run(
        enrich_with_wikipedia(
            min_chars=args.min_chars,
            limit=args.limit,
            concurrency=args.concurrency,
            batch_commit=args.batch_commit,
            dry_run=args.dry_run,
        )
    )


if __name__ == "__main__":
    main()
