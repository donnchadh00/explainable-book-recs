from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.book import Book
from app.services.embeddings import Embedder
from app.services.recs import hybrid_recommendations
from app.services.explain import explain_similarity

router = APIRouter(prefix="/recommend", tags=["recommend"])

EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
_embedder = Embedder(EMBED_MODEL)


@router.get("")
def recommend(
    # Inputs
    q: Optional[str] = Query(None, description="Free-text semantic query"),
    seed_book_id: Optional[int] = Query(None, description="Seed book (vector similarity)"),
    user_id: Optional[int] = Query(None, description="User id for CF (optional)"),

    # Top-level channel weights
    w_cf: float = Query(0.0, ge=0.0, le=1.0),
    w_semantic: float = Query(1.0, ge=0.0, le=1.0),

    # Inside the semantic channel: seed vs query mixing
    w_seed: float = Query(0.5, ge=0.0, le=1.0, description="Weight for seed similarity inside semantic"),
    w_query: float = Query(0.5, ge=0.0, le=1.0, description="Weight for query hybrid inside semantic"),

    # The internal text/vector mix used by the query channel (matching /search/semantic)
    hybrid_weight: float = Query(0.7, ge=0.0, le=1.0),

    # Optional filters for the *query* channel (to mirror /search/semantic)
    lang: Optional[str] = None,
    fiction: Optional[bool] = None,
    min_year: Optional[int] = None,
    max_pages: Optional[int] = None,
    exclude_rated_user_id: Optional[int] = None,

    # Misc
    k: int = Query(20, ge=1, le=100),

    db: Session = Depends(get_db),
):
    if not (q or seed_book_id or user_id):
        raise HTTPException(400, "Provide at least one of q, seed_book_id, or user_id")

    base_book: Book | None = None
    if seed_book_id is not None:
        base_book = db.execute(select(Book).where(Book.id == seed_book_id)).scalar_one_or_none()
        if base_book is None:
            raise HTTPException(404, detail=f"Seed book {seed_book_id} not found")

    # Run the orchestrator
    recs = hybrid_recommendations(
        db,
        user_id=user_id,
        seed_book_id=seed_book_id,
        query=(q.strip() if q else None),
        k=k,
        w_cf=w_cf,
        w_semantic=w_semantic,
        embedder=_embedder,
        w_sem_seed=w_seed,
        w_sem_query=w_query,
        hybrid_weight=hybrid_weight,
        lang=lang, fiction=fiction,
        min_year=min_year, max_pages=max_pages,
        exclude_rated_user_id=exclude_rated_user_id,
    )

    # Format response + explanations
    results = []
    for book, score, parts in recs:
        if base_book:
            reason = explain_similarity(base_book, book, parts)  # smart seed-based reason
        else:
            bits = []
            if parts.get("cf", 0) > 0.01:
                bits.append("liked by similar readers")
            if parts.get("semantic", 0) > 0.01:
                bits.append("close in theme/description")
            reason = " / ".join(bits) or "overall similarity"

        results.append({
            "id": book.id,
            "title": book.title,
            "author": getattr(book, "author", None),
            "published_year": getattr(book, "published_year", None),
            "score": float(f"{score:.6f}"),
            "channels": {
                "cf": float(f"{parts.get('cf', 0.0):.6f}"),
                "semantic": float(f"{parts.get('semantic', 0.0):.6f}"),
            },
            "reason": reason,
        })

    return {
        "query": q,
        "seed_book_id": seed_book_id,
        "user_id": user_id,
        "k": k,
        "weights": {
            "cf": w_cf,
            "semantic": w_semantic,
            "semantic_seed": w_seed,
            "semantic_query": w_query,
            "semantic_text_vector_hybrid": hybrid_weight,
        },
        "results": results,
    }
