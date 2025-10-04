from __future__ import annotations
import argparse
import asyncio
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from app.db import SessionLocal
from app.models.book import Book

OL_SEARCH   = "https://openlibrary.org/search.json"
OL_WORK     = "https://openlibrary.org{work_key}.json"
OL_EDITIONS = "https://openlibrary.org{work_key}/editions.json"
OL_AUTHOR   = "https://openlibrary.org{author_key}.json"

# helpers

def _clean_year(s: Optional[str]) -> Optional[int]:
    if not s:
        return None
    m = re.search(r"(17|18|19|20)\d{2}", s)
    return int(m.group(0)) if m else None

def _clean_isbn13(isbns: Iterable[str]) -> Optional[str]:
    for raw in isbns or []:
        s = re.sub(r"[^0-9Xx]", "", str(raw))
        if len(s) == 13 and s.isdigit():
            return s
    return None

def _norm_subject(s: str) -> str:
    s = s.strip()
    if s.startswith(("subject_key:", "subject:")):
        s = s.split(":", 1)[1].strip().strip('"').strip("'")
    return s

def _detect_language_code(ed: Dict) -> Optional[str]:
    langs = ed.get("languages") or []
    for L in langs:
        key = (L.get("key") or "")
        if key.startswith("/languages/"):
            return key.split("/")[-1]  # e.g. 'eng'
    return None

def _is_fictionish(title: str, subjects_list: List[str]) -> bool:
    t = (title or "").lower()
    if "novel" in t:
        return True
    subs = [s.lower() for s in subjects_list or []]
    return (
        "fiction" in " ".join(subs)
        or any("novel" in s for s in subs)
        or any(s in subs for s in [
            "gothic fiction", "science fiction", "fantasy",
            "detective and mystery stories", "dystopias",
            "satire", "classics", "classic literature",
        ])
    )

# caching

class JsonCache:
    def __init__(self, root: Optional[Path]):
        self.root = root
        if self.root:
            self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", key)
        return (self.root / f"{safe}.json")  # type: ignore

    def get(self, key: str) -> Optional[dict]:
        if not self.root:
            return None
        p = self._path(key)
        if p.exists():
            try:
                return json.loads(p.read_text())
            except Exception:
                return None
        return None

    def put(self, key: str, data: dict) -> None:
        if not self.root:
            return
        p = self._path(key)
        try:
            p.write_text(json.dumps(data, ensure_ascii=False))
        except Exception:
            pass

# async fetch helpers

async def fetch_json(client: httpx.AsyncClient, url: str, params: dict | None = None,
                     retries: int = 3, backoff: float = 0.5) -> dict:
    last = None
    for i in range(retries):
        try:
            r = await client.get(url, params=params, timeout=30)
            if r.status_code in (429, 500, 502, 503, 504):
                await asyncio.sleep(backoff * (2 ** i))
                continue
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last = e
            await asyncio.sleep(backoff * (2 ** i))
    raise last or RuntimeError(f"Failed to GET {url}")

async def fetch_search(client: httpx.AsyncClient, subjects: List[str], queries: List[str],
                       page: int, limit: int) -> Dict:
    params = {"page": page, "limit": limit}
    if subjects:
        params["subject"] = subjects[0]
    if queries:
        params["q"] = queries[0]
    return await fetch_json(client, OL_SEARCH, params)

async def fetch_work(client: httpx.AsyncClient, work_key: str, cache: JsonCache | None) -> Dict:
    ckey = f"work_{work_key}"
    if cache:
        hit = cache.get(ckey)
        if hit is not None:
            return hit
    data = await fetch_json(client, OL_WORK.format(work_key=work_key))
    if cache:
        cache.put(ckey, data)
    return data

async def fetch_editions(client: httpx.AsyncClient, work_key: str, limit: int,
                         cache: JsonCache | None) -> Dict:
    ckey = f"editions_{work_key}_{limit}"
    if cache:
        hit = cache.get(ckey)
        if hit is not None:
            return hit
    data = await fetch_json(client, OL_EDITIONS.format(work_key=work_key),
                            params={"limit": limit, "offset": 0})
    if cache:
        cache.put(ckey, data)
    return data

async def fetch_author_name(client: httpx.AsyncClient, author_key: str,
                            cache: JsonCache | None) -> Optional[str]:
    """Resolve '/authors/OLxxxA' to a display name, cached."""
    ckey = f"author_{author_key}"
    if cache:
        hit = cache.get(ckey)
        if hit is not None:
            return hit.get("name")
    data = await fetch_json(client, OL_AUTHOR.format(author_key=author_key))
    name = (data.get("name") or "").strip() or None
    if cache:
        cache.put(ckey, {"name": name})
    return name

# parsing & selection

def parse_work_payload(work: Dict) -> Tuple[str, List[str], str, List[str]]:
    """
    Returns: (title, author_keys, description, subjects)
    """
    title = (work.get("title") or "").strip()

    # description: string | dict{value} | list of strings
    desc = work.get("description")
    if isinstance(desc, dict):
        desc = desc.get("value")
    elif isinstance(desc, list):
        desc = " ".join([str(x) for x in desc if isinstance(x, (str, bytes))])
    if desc is None:
        desc = ""

    subjects: List[str] = []
    for s in (work.get("subjects") or []):
        if isinstance(s, str):
            subjects.append(s)
        elif isinstance(s, dict) and "name" in s:
            subjects.append(s["name"])

    author_keys: List[str] = []
    for a in (work.get("authors") or []):
        if isinstance(a, dict):
            ak = a.get("author", {}).get("key")
            if isinstance(ak, str) and ak.startswith("/authors/"):
                author_keys.append(ak)

    return title, author_keys, str(desc).strip(), subjects

def choose_best_edition(editions: List[Dict]) -> Optional[Dict]:
    """
    Prefer English-language editions; among those, prefer (has ISBN13, more pages, newer year).
    """
    if not editions:
        return None

    def is_eng(ed):
        langs = ed.get("languages") or []
        for L in langs:
            key = (L.get("key") or "")
            if key.endswith("/eng"):
                return True
        return False

    def score(ed):
        isbn13 = _clean_isbn13(ed.get("isbn_13") or [])
        has_isbn = 1 if isbn13 else 0
        pages = ed.get("number_of_pages") or 0
        year = _clean_year(ed.get("publish_date") or "")
        return (has_isbn, pages, year or 0)

    pool = [e for e in editions if is_eng(e)] or editions
    pool.sort(key=score, reverse=True)
    return pool[0] if pool else None

# DB upserts

def upsert_book(
    db: Session,
    title: str,
    author: Optional[str],
    isbn13: Optional[str],
    page_count: Optional[int],
    published_year: Optional[int],
    description: Optional[str],
    language_code: Optional[str],
    is_fiction: Optional[bool],
) -> int:
    table_cols = set(Book.__table__.columns.keys())
    values = dict(
        title=title,
        author=author,
        isbn13=isbn13,
        page_count=page_count,
        published_year=published_year,
        description=description,
    )
    if "language_code" in table_cols:
        values["language_code"] = language_code
    if "is_fiction" in table_cols:
        values["is_fiction"] = is_fiction

    if isbn13:
        stmt_base = insert(Book).values(**values)
        set_map = {
            col: getattr(stmt_base.excluded, col)
            for col in values.keys() if col != "isbn13"
        }
        stmt = (
            stmt_base
            .on_conflict_do_update(index_elements=["isbn13"], set_=set_map)
            .returning(Book.id)
        )
        return db.execute(stmt).scalar_one()

    existing = db.execute(
        select(Book.id).where(Book.title == title, Book.author == author)
    ).scalar()
    if existing:
        db.query(Book).filter(Book.id == existing).update(
            {k: v for k, v in values.items() if k in table_cols and k != "isbn13"}
        )
        db.flush()
        return existing

    b = Book(**{k: v for k, v in values.items() if k in table_cols})
    db.add(b)
    db.flush()
    return b.id

# main ingest

async def ingest_openlibrary_async(
    subjects: List[str],
    queries: List[str],
    per_source_max: int,
    editions_limit: int,
    concurrency: int,
    batch_commit: int,
    cache_dir: Optional[str],
):
    total_seen = 0
    total_upserted = 0
    total_errors = 0
    seen_work_keys: set[str] = set()

    cache = JsonCache(Path(cache_dir) if cache_dir else None)

    limits = httpx.Limits(
        max_keepalive_connections=concurrency,
        max_connections=concurrency * 2
    )

    async with httpx.AsyncClient(http2=True, timeout=30, limits=limits,
                                 headers={"User-Agent": "book-recs/ingest"}) as client:
        with SessionLocal() as db:
            pending_since_commit = 0
            sem = asyncio.Semaphore(concurrency)

            async def process_doc(d: dict):
                nonlocal total_seen, total_upserted, total_errors, pending_since_commit
                work_key = d.get("key")
                if not work_key or work_key in seen_work_keys:
                    return
                async with sem:
                    try:
                        work, eds = await asyncio.gather(
                            fetch_work(client, work_key, cache),
                            fetch_editions(client, work_key, editions_limit, cache),
                        )
                    except Exception:
                        total_errors += 1
                        return

                    title, author_keys, work_desc, subjects_list = parse_work_payload(work)
                    best = choose_best_edition((eds.get("entries") or []))

                    # Edition-side metadata fallbacks
                    isbn13 = page_count = year = language_code = None
                    edition_desc = None
                    if best:
                        isbn13 = _clean_isbn13(best.get("isbn_13") or [])
                        page_count = best.get("number_of_pages")
                        year = _clean_year(best.get("publish_date") or "")
                        language_code = _detect_language_code(best)
                        ed_desc = best.get("description")
                        if isinstance(ed_desc, dict):
                            ed_desc = ed_desc.get("value")
                        if isinstance(ed_desc, str):
                            edition_desc = ed_desc.strip()

                    description = (work_desc or "").strip()
                    if not description and edition_desc:
                        description = edition_desc

                    # Resolve a readable author name
                    author_name: Optional[str] = None
                    if author_keys:
                        # just take the first author for MVP
                        try:
                            author_name = await fetch_author_name(client, author_keys[0], cache)
                        except Exception:
                            author_name = None
                    if not author_name and best:
                        author_name = (best.get("by_statement") or "").strip() or None

                    # Tag subjects into description so embeddings “see” themes
                    tag_str = " | ".join(subjects_list[:20]) if subjects_list else ""
                    if tag_str:
                        if description:
                            description = f"{description}\n\nSubjects: {tag_str}"
                        else:
                            description = f"Subjects: {tag_str}"

                    is_fiction = _is_fictionish(title, subjects_list)

                    try:
                        _ = upsert_book(
                            db=db,
                            title=title,
                            author=author_name,
                            isbn13=isbn13,
                            page_count=(int(page_count) if page_count else None),
                            published_year=year,
                            description=(description or None),
                            language_code=language_code,
                            is_fiction=is_fiction,
                        )
                        pending_since_commit += 1
                        total_upserted += 1
                    except Exception:
                        db.rollback()
                        total_errors += 1
                        return

                    total_seen += 1
                    seen_work_keys.add(work_key)

                    if pending_since_commit >= batch_commit:
                        db.commit()
                        pending_since_commit = 0

            async def run_source(source_type: str, source: str):
                seen_for_source = 0
                page = 1
                while seen_for_source < per_source_max:
                    try:
                        data = await fetch_search(
                            client,
                            subjects=[_norm_subject(source)] if source_type == "subject" else [],
                            queries=[source] if source_type == "query" else [],
                            page=page,
                            limit=100,
                        )
                    except Exception:
                        break

                    docs = data.get("docs") or []
                    if not docs:
                        break

                    tasks = []
                    for d in docs:
                        if seen_for_source >= per_source_max:
                            break
                        tasks.append(asyncio.create_task(process_doc(d)))
                        seen_for_source += 1

                    if tasks:
                        await asyncio.gather(*tasks)

                    page += 1
                    num_found = data.get("numFound") or 0
                    if (page - 1) * 100 >= num_found:
                        break

            # Subjects then queries
            for source in subjects:
                await run_source("subject", source)
            for source in queries:
                await run_source("query", source)

            db.commit()

    print(f"Done. Seen works: {total_seen}, upserted rows: {total_upserted}, errors: {total_errors}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", action="append", default=[], help="Open Library subject slug (e.g. classic_literature, modernism). May repeat.")
    ap.add_argument("--query", action="append", default=[], help="Free-text query. May repeat.")
    ap.add_argument("--max-per-source", type=int, default=500, help="Max works per subject or query (cap).")
    ap.add_argument("--editions-limit", type=int, default=40, help="How many editions to scan per work (lower is faster, often enough).")
    ap.add_argument("--concurrency", type=int, default=24, help="Parallel HTTP calls.")
    ap.add_argument("--batch-commit", type=int, default=200, help="Commit every N upserts.")
    ap.add_argument("--cache-dir", type=str, default="etl_cache", help="Directory for JSON cache (empty string to disable).")
    args = ap.parse_args()

    asyncio.run(
        ingest_openlibrary_async(
            subjects=args.subject,
            queries=args.query,
            per_source_max=args.max_per_source,
            editions_limit=args.editions_limit,
            concurrency=args.concurrency,
            batch_commit=args.batch_commit,
            cache_dir=(args.cache_dir or None),
        )
    )

if __name__ == "__main__":
    main()
