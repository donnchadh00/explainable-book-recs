import os
import argparse
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
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

def upsert_book(db: Session, row: dict) -> int:
    stmt = insert(Book).values(
        title=row.get("title"),
        author=row.get("author"),
        isbn13=(str(row.get("isbn13")) if pd.notna(row.get("isbn13")) else None),
        page_count=int(row["page_count"]) if pd.notna(row.get("page_count")) else None,
        published_year=int(row["published_year"]) if pd.notna(row.get("published_year")) else None,
    ).on_conflict_do_update(
        index_elements=["isbn13"],
        set_={
            "title": insert(Book).excluded.title,
            "author": insert(Book).excluded.author,
            "page_count": insert(Book).excluded.page_count,
            "published_year": insert(Book).excluded.published_year,
        },
    ).returning(Book.id)
    res = db.execute(stmt).scalar()
    if res is None:
        # fallback: if no isbn13, try title+author existence
        existing = db.query(Book).filter(
            Book.title==row.get("title"), Book.author==row.get("author")
        ).first()
        if existing:
            return existing.id
        db.add(Book(
            title=row.get("title"),
            author=row.get("author"),
            page_count=int(row["page_count"]) if pd.notna(row.get("page_count")) else None,
            published_year=int(row["published_year"]) if pd.notna(row.get("published_year")) else None,
        ))
        db.flush()
        return db.query(Book).filter(Book.title==row.get("title"), Book.author==row.get("author")).first().id
    return res

def read_goodreads_csv(path: str) -> pd.DataFrame:
    encodings = ["utf-8", "utf-8-sig", "cp1252", "latin-1", "utf-16"]
    last_err = None
    for enc in encodings:
        try:
            return pd.read_csv(
                path,
                encoding=enc,
                engine="python",
                dtype={"ISBN13": "string"}
            )
        except Exception as e:
            last_err = e
    raise RuntimeError(f"Failed to read CSV with encodings {encodings}: {last_err}")

def load_csv(path: str):
    df = read_goodreads_csv(path)
    df = df.rename(columns=COL_MAP)
    df["rated_at"] = pd.to_datetime(df.get("rated_at"), errors="coerce")
    df = df[df["rating"].notna()]

    db = SessionLocal()
    inserted_books = 0
    inserted_ratings = 0
    try:
        for _, r in df.iterrows():
            book_id = upsert_book(db, r.to_dict())
            # upsert rating (user_id=1 for MVP)
            db.merge(Rating(
                user_id=1,
                book_id=book_id,
                rating=float(r["rating"]) if pd.notna(r["rating"]) else None,
                rated_at=pd.to_datetime(r["rated_at"]) if pd.notna(r.get("rated_at")) else None,
                source="goodreads",
            ))
            inserted_ratings += 1
            inserted_books += 1
        db.commit()
        print(f"Done. Books processed ~{inserted_books}, ratings inserted {inserted_ratings}.")
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="Path to Goodreads CSV export")
    args = parser.parse_args()
    load_csv(args.csv)
