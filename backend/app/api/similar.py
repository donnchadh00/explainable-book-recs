from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from pgvector.sqlalchemy import Vector
from app.db import get_db

router = APIRouter(prefix="/books", tags=["books"])

@router.get("/{book_id}/similar")
def similar_books(book_id: int, k: int = 20, db: Session = Depends(get_db)):
    sql = """
      SELECT b2.id, b2.title, b2.author, b2.published_year, b2.page_count,
             1 - (e2.vector <=> e1.vector) AS cosine
      FROM embeddings e1
      JOIN embeddings e2 ON e2.entity_type = 'book' AND e2.entity_id != e1.entity_id
      JOIN books b2 ON b2.id = e2.entity_id
      WHERE e1.entity_type = 'book' AND e1.entity_id = :id
      ORDER BY e2.vector <=> e1.vector
      LIMIT :k
    """
    rows = db.execute(text(sql), {"id": book_id, "k": k}).mappings().all()
    if not rows:
        raise HTTPException(404, "No embedding found for that book")
    return {"book_id": book_id, "results": [
        {**dict(r), "cosine": float(f"{r['cosine']:.6f}")} for r in rows
    ]}
