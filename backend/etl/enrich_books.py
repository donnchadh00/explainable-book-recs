from __future__ import annotations
import json
import hashlib
from pathlib import Path
from typing import Iterable, Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.models.book import Book
from app.models import embedding
from app.models.embedding import Embedding
from .enrich_openlibrary import (
    fetch_by_isbn as ol_fetch,
    parse_ol_payload,
    fetch_work_by_title_author,
    parse_work_payload,
)
from .enrich_googlebooks import fetch_by_isbn as gb_fetch, parse_gb_payload

CACHE = Path(__file__).with_name("cache")
CACHE.mkdir(exist_ok=True, parents=True)

def _cache_get(key: str) -> dict | None:
    p = CACHE / f"{key}.json"
    return json.loads(p.read_text()) if p.exists() else None

def _cache_put(key: str, payload: dict) -> None:
    p = CACHE / f"{key}.json"
    p.write_text(json.dumps(payload, ensure_ascii=False))

def _ta_key(title: str, author: Optional[str]) -> str:
    base = (title or "").strip().lower() + "||" + ((author or "").strip().lower())
    return "ta_" + hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]

def candidates(db: Session) -> Iterable[Book]:
    # include non-ISBN rows so title+author fallback can run
    stmt = select(Book).where(
        (Book.description.is_(None)) | (Book.page_count.is_(None)) | (Book.published_year.is_(None))
    ).limit(5000)
    return db.scalars(stmt)

def upsert_subjects(db: Session, book_id: int, subjects: list[str]):
    try:
        for name in {s.strip().lower() for s in subjects if s and s.strip()}:
            gid = db.execute(
                select(db.text("id")).select_from(db.text("genres")).where(db.text("name = :n")),
                {"n": name},
            ).scalar()
            if gid is None:
                gid = db.execute(
                    db.text("INSERT INTO genres(name) VALUES (:n) RETURNING id"),
                    {"n": name},
                ).scalar()
            db.execute(
                db.text(
                    "INSERT INTO book_genres(book_id, genre_id, confidence) "
                    "VALUES (:b, :g, 1.0) ON CONFLICT (book_id, genre_id) DO NOTHING"
                ),
                {"b": book_id, "g": gid},
            )
    except Exception:
        db.rollback()

def run(limit: Optional[int] = None):
    with SessionLocal() as db:
        totals = db.execute(
            select(
                func.count(),
                func.count().filter(Book.isbn13.is_not(None)),
                func.count().filter(Book.isbn13.is_(None)),
                func.count().filter(Book.description.is_not(None)),
            )
        ).one()
        print(f"Totals: all={totals[0]}, with_isbn={totals[1]}, no_isbn={totals[2]}, with_desc={totals[3]}")

        updated = 0
        for book in candidates(db):
            if limit and updated >= limit:
                break

            isbn = book.isbn13
            title = book.title
            author = getattr(book, "author", None)
            cache_key = isbn if isbn else _ta_key(title, author)

            cached = _cache_get(cache_key)
            if cached and cached.get("nothing_found"):
                continue

            ol_data = (cached or {}).get("ol")
            gb_data = (cached or {}).get("gb")
            work_data = (cached or {}).get("work")

            # Open Library by ISBN (edition -> work)
            if isbn and ol_data is None:
                try:
                    ed = ol_fetch(isbn)
                    d, subs, pages, year = parse_ol_payload(ed)
                    ol_data = {"desc": d, "subs": subs, "pages": pages, "year": year}
                except Exception:
                    ol_data = None

            # Google Books fallback (only if still missing)
            need_gb = isbn and not (ol_data and (ol_data.get("desc") or ol_data.get("pages") or ol_data.get("year")))
            if need_gb and gb_data is None:
                try:
                    gb_raw = gb_fetch(isbn)
                    d, subs, pages, year = parse_gb_payload(gb_raw)
                    gb_data = {"desc": d, "subs": subs, "pages": pages, "year": year}
                except Exception:
                    gb_data = None

            # Open Library Work search by title+author (for no-ISBN OR still no desc)
            need_work = (not isbn) or not (
                (ol_data and ol_data.get("desc")) or (gb_data and gb_data.get("desc"))
            )
            if need_work and work_data is None:
                print("openlibrary 222\n")
                work_desc, work_subs = None, []
                try:
                    work = fetch_work_by_title_author(title, author)
                    if work:
                        work_desc, work_subs = parse_work_payload(work)
                except Exception:
                    pass
                work_data = {"desc": work_desc, "subs": work_subs}

            # assemble best values
            desc = ( (ol_data or {}).get("desc")
                  |  (gb_data or {}).get("desc")
                  |  (work_data or {}).get("desc") ) if False else (
                     (ol_data or {}).get("desc")
                  or (gb_data or {}).get("desc")
                  or (work_data or {}).get("desc")
            )
            subs = ( (ol_data or {}).get("subs")
                  or (gb_data or {}).get("subs")
                  or (work_data or {}).get("subs")
                  or [] )
            pages = ( (ol_data or {}).get("pages")
                   or (gb_data or {}).get("pages") )
            year  = ( (ol_data or {}).get("year")
                   or (gb_data or {}).get("year") )

            # cache the outcome (including nothing_found marker)
            payload = {"ol": ol_data, "gb": gb_data, "work": work_data}
            if not (desc or pages or year):
                payload["nothing_found"] = True
            _cache_put(cache_key, payload)

            # persist changes
            changed = False
            if desc and not book.description:
                book.description = desc.strip() or None
                changed = True
            if pages and not book.page_count:
                try:
                    book.page_count = int(pages)
                    changed = True
                except Exception:
                    pass
            if year and not book.published_year:
                try:
                    book.published_year = int(year)
                    changed = True
                except Exception:
                    pass

            if changed:
                db.add(book)
                db.commit()
                print(f"• Updated #{book.id} — desc={'✓' if desc else '·'}, pages={'✓' if pages else '·'}, year={'✓' if year else '·'}")
                updated += 1

            if subs:
                try:
                    upsert_subjects(db, book.id, subs)
                    db.commit()
                except Exception:
                    db.rollback()

        print(f"Enrichment updated {updated} books")


if __name__ == "__main__":
    run()
