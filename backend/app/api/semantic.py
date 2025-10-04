from __future__ import annotations
import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text, bindparam
from sqlalchemy.orm import Session
from pgvector.sqlalchemy import Vector

from ..db import get_db
from ..services.embeddings import Embedder

router = APIRouter(prefix="/search", tags=["search"])

EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
EMBED_DIM = int(os.getenv("EMBED_DIM", "384"))

_embedder = Embedder(EMBED_MODEL)

@router.get("/semantic")
def semantic_search(
    q: str,
    k: int = 20,
    min_year: int | None = None,
    max_pages: int | None = None,
    exclude_rated_user_id: int | None = None,
    # make filters opt-in (None means: don't filter)
    lang: str | None = None,
    fiction: bool | None = None,
    hybrid_weight: float = 0.7,
    db: Session = Depends(get_db),
):
    """
    Semantic (vector) search over books with optional hybrid scoring:
      hybrid = w * vscore + (1 - w) * tscore

    vscore = 1 - (e.vector <=> :qvec)             -- cosine sim
    tscore = ts_rank(to_tsvector(title+desc), plainto_tsquery(q))
    """
    q = (q or "").strip()
    if not q:
        raise HTTPException(400, detail="Query 'q' is required")

    qvec = _embedder.encode_query(q)

    base_sql = """
        WITH scored AS (
          SELECT
            b.id, b.title, b.author, b.published_year, b.page_count, b.description,
            (1 - (e.vector <=> :qvec))::float8 AS vscore,
            ts_rank(
              to_tsvector('simple', coalesce(b.title,'') || ' ' || coalesce(b.description,'')),
              plainto_tsquery(:q)
            )::float8 AS tscore
          FROM embeddings e
          JOIN books b ON b.id = e.entity_id
          WHERE e.entity_type = 'book'
    """

    # Only add filters if provided
    if lang is not None and lang != "":
        base_sql += " AND b.language_code = :lang"
    if fiction is not None:
        base_sql += " AND b.is_fiction IS NOT NULL AND b.is_fiction = :is_fiction"
    if min_year is not None:
        base_sql += " AND (b.published_year IS NULL OR b.published_year >= :min_year)"
    if max_pages is not None:
        base_sql += " AND (b.page_count IS NULL OR b.page_count <= :max_pages)"
    if exclude_rated_user_id is not None:
        base_sql += """
          AND NOT EXISTS (
            SELECT 1 FROM ratings r WHERE r.book_id = b.id AND r.user_id = :uid
          )
        """

    base_sql += """
        )
        SELECT id, title, author, published_year, page_count, description,
               vscore, tscore, (:w * vscore + (1 - :w) * tscore) AS hybrid
        FROM scored
        ORDER BY hybrid DESC
        LIMIT :k
    """

    stmt = text(base_sql).bindparams(bindparam("qvec", type_=Vector(EMBED_DIM)))

    params: dict = {"qvec": qvec, "q": q, "k": k, "w": float(hybrid_weight)}
    if lang is not None and lang != "":
        params["lang"] = lang
    if fiction is not None:
        params["is_fiction"] = bool(fiction)
    if min_year is not None:
        params["min_year"] = min_year
    if max_pages is not None:
        params["max_pages"] = max_pages
    if exclude_rated_user_id is not None:
        params["uid"] = exclude_rated_user_id

    rows = db.execute(stmt, params).mappings().all()

    def snip(s: str | None) -> str | None:
        if not s:
            return None
        s = s.strip().replace("\n", " ")
        return (s[:200] + "…") if len(s) > 200 else s

    return {
        "query": q,
        "k": k,
        "results": [
            {
                "id": r["id"],
                "title": r["title"],
                "author": r["author"],
                "published_year": r["published_year"],
                "page_count": r["page_count"],
                "cosine": float(f"{r['vscore']:.6f}"),
                "snippet": snip(r["description"]),
            }
            for r in rows
        ],
    }
