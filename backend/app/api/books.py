from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.book import Book

router = APIRouter(prefix="/books", tags=["books"])

@router.get("")
def list_books(q: str | None = None, limit: int = 20, db: Session = Depends(get_db)):
    stmt = select(Book).limit(limit)
    if q:
        stmt = select(Book).where(Book.title.ilike(f"%{q}%")).limit(limit)
    rows = db.execute(stmt).scalars().all()
    return [{"id": b.id, "title": b.title, "author": b.author} for b in rows]

@router.get("/search")
def search_books(q: str = Query(..., min_length=2), k: int = 10, db: Session = Depends(get_db)):
    """
    Simple title/author substring search for use in frontend autocomplete.
    """
    sql = text("""
        SELECT id, title, author, published_year
        FROM books
        WHERE title ILIKE :pattern OR author ILIKE :pattern
        ORDER BY published_year DESC NULLS LAST
        LIMIT :k
    """)
    rows = db.execute(sql, {"pattern": f"%{q}%", "k": k}).mappings().all()
    return {"results": [dict(r) for r in rows]}
