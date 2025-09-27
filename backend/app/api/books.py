from fastapi import APIRouter, Depends
from sqlalchemy import select
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
