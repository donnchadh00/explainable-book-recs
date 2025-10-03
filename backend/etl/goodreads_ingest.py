import os
import argparse
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import text
from app.db import SessionLocal
from app.models import Book, Rating

COL_MAP = {
    "Title": "title",
    "Author": "author",
    "My Rating": "rating",
    "ISBN13": "isbn13",
    "Number of Pages": "page_count",
    "Original Publication Year": "published_year",
    "Date Read": "rated_at",
}

def _clean_isbn13(v) -> str | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip()
    if not s or s.lower() == "nan":
        return None
    # keep only digits and X/x
    s = "".join(ch for ch in s if ch.isdigit() or ch in "Xx")
    return s or None

def get_or_create_user(db: Session, display_name: str, source: str) -> int:
    """Use raw SQL so we don't need a User ORM model."""
    existing = db.execute(
        text("SELECT id FROM users WHERE display_name = :n AND source = :s LIMIT 1"),
        {"n": display_name, "s": source},
    ).scalar()
    if existing:
        return existing
    new_id = db.execute(
        text("INSERT INTO users(display_name, source) VALUES (:n, :s) RETURNING id"),
        {"n": display_name, "s": source},
    ).scalar()
    db.commit()
    return new_id

def upsert_book(db: Session, row: dict) -> int:
    isbn13 = _clean_isbn13(row.get("isbn13"))

    if isbn13:
        stmt = insert(Book).values(
            title=row.get("title"),
            author=row.get("author"),
            isbn13=isbn13,
            page_count=int(row["page_count"]) if pd.notna(row.get("page_count")) else None,
            published_year=int(row["published_year"]) if pd.notna(row.get("published_year")) else None,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["isbn13"],
            set_={
                "title": stmt.excluded.title,
                "author": stmt.excluded.author,
                "page_count": stmt.excluded.page_count,
                "published_year": stmt.excluded.published_year,
            },
        ).returning(Book.id)
        res = db.execute(stmt).scalar()
        if res is not None:
            return res

    # Fallback: no/invalid ISBN13 — try title+author match
    existing = db.query(Book).filter(
        Book.title == row.get("title"), Book.author == row.get("author")
    ).first()
    if existing:
        return existing.id

    # Insert a new book without ISBN
    b = Book(
        title=row.get("title"),
        author=row.get("author"),
        page_count=int(row["page_count"]) if pd.notna(row.get("page_count")) else None,
        published_year=int(row["published_year"]) if pd.notna(row.get("published_year")) else None,
        isbn13=None,
    )
    db.add(b)
    db.flush()
    return b.id

def read_goodreads_csv(path: str) -> pd.DataFrame:
    encodings = ["utf-8", "utf-8-sig", "cp1252", "latin-1", "utf-16"]
    last_err = None
    for enc in encodings:
        try:
            return pd.read_csv(
                path,
                encoding=enc,
                engine="python",
                dtype={"ISBN13": "string"},
            )
        except Exception as e:
            last_err = e
    raise RuntimeError(f"Failed to read CSV with encodings {encodings}: {last_err}")

def load_csv(path: str, user_name: str, user_source: str):
    df = read_goodreads_csv(path)
    df = df.rename(columns=COL_MAP)
    df["rated_at"] = pd.to_datetime(df.get("rated_at"), errors="coerce")
    df = df[df["rating"].notna()]

    db = SessionLocal()
    inserted_books = 0
    inserted_ratings = 0
    try:
        user_id = get_or_create_user(db, display_name=user_name, source=user_source)

        for _, r in df.iterrows():
            book_id = upsert_book(db, r.to_dict())

            # Upsert/merge rating for this user+book
            db.merge(
                Rating(
                    user_id=user_id,
                    book_id=book_id,
                    rating=float(r["rating"]) if pd.notna(r["rating"]) else None,
                    rated_at=pd.to_datetime(r["rated_at"]) if pd.notna(r.get("rated_at")) else None,
                    source="goodreads",
                )
            )

            inserted_ratings += 1
            inserted_books += 1

        db.commit()
        print(
            f"Done. Books processed ≈{inserted_books}, ratings inserted/updated {inserted_ratings} "
            f"for user '{user_name}' ({user_source})."
        )
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="Path to Goodreads CSV export")
    parser.add_argument("--user-name", default="Demo User", help="Display name for the ingest user")
    parser.add_argument("--user-source", default="goodreads", help="Source label for the ingest user")
    args = parser.parse_args()
    load_csv(args.csv, user_name=args.user_name, user_source=args.user_source)
