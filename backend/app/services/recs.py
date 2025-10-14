from __future__ import annotations

import os
from typing import Dict, Iterable, List, Tuple, Optional

from sqlalchemy import select, text, bindparam
from sqlalchemy.orm import Session
from pgvector.sqlalchemy import Vector

from app.models.book import Book
from app.models.embedding import Embedding
from app.services.embeddings import Embedder
from app.services.cf import (
    recommend_for_user,
    similar_books_by_ratings,
    fetch_books_by_ids,
)
from dotenv import load_dotenv

load_dotenv()

EMBED_DIM = int(os.getenv("EMBED_DIM", "384"))


def _minmax_norm(scores: Dict[int, float]) -> Dict[int, float]:
    """
    Normalize a score dict to [0,1]. If all values are equal, returns zeros.
    """
    if not scores:
        return {}
    vals = list(scores.values())
    lo, hi = min(vals), max(vals)
    if hi <= lo:
        return {k: 0.0 for k in scores}
    return {k: (v - lo) / (hi - lo) for k, v in scores.items()}


# Semantic helpers

def semantic_similar_to_book(db: Session, book_id: int, k: int = 20) -> List[Tuple[int, float]]:
    """
    Given a book id, fetch its vector then find nearest neighbors in embeddings.
    Returns [(other_book_id, cosine_sim)] (cosine in [0..1]).
    """
    row = db.execute(
        select(Embedding.vector).where(
            Embedding.entity_type == "book", Embedding.entity_id == book_id
        )
    ).first()
    if not row:
        return []

    vec = row[0]  # pgvector returns a list[float] via SQLAlchemy

    stmt = text("""
        SELECT b.id AS bid, (1 - (e.vector <=> :v))::float8 AS sim
        FROM embeddings e
        JOIN books b ON b.id = e.entity_id
        WHERE e.entity_type = 'book' AND b.id != :bid
        ORDER BY e.vector <=> :v
        LIMIT :k
    """).bindparams(bindparam("v", type_=Vector(len(vec))))

    rows = db.execute(stmt, {"v": vec, "k": k, "bid": book_id}).all()
    return [(int(r.bid), float(r.sim)) for r in rows]


def semantic_from_query_hybrid(
    db: Session,
    embedder: Embedder,
    q: str,
    k: int = 20,
    hybrid_weight: float = 0.7,
    *,
    lang: str | None = None,
    fiction: bool | None = None,
    min_year: int | None = None,
    max_pages: int | None = None,
    exclude_rated_user_id: int | None = None,
) -> List[Tuple[int, float]]:
    """
    Hybrid query scoring that MATCHES app/api/semantic.py:
      vscore = 1 - (e.vector <=> :qvec)
      tscore = ts_rank(to_tsvector(title+description), plainto_tsquery(q))
      hybrid = w * vscore + (1 - w) * tscore

    Returns [(book_id, hybrid_score)] ordered desc by hybrid.
    """
    qvec = embedder.encode_query(q)

    base_sql = """
        WITH scored AS (
          SELECT
            b.id,
            (1 - (e.vector <=> :qvec))::float8 AS vscore,
            ts_rank(
              to_tsvector('simple', coalesce(b.title,'') || ' ' || coalesce(b.description,'')),
              plainto_tsquery(:q)
            )::float8 AS tscore
          FROM embeddings e
          JOIN books b ON b.id = e.entity_id
          WHERE e.entity_type = 'book'
    """

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
        SELECT id, (:w * vscore + (1 - :w) * tscore) AS hybrid
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

    rows = db.execute(stmt, params).all()
    return [(int(r.id), float(r.hybrid)) for r in rows]


# Hybrid combiner

def hybrid_recommendations(
    db: Session,
    *,
    user_id: Optional[int] = None,
    seed_book_id: Optional[int] = None,
    query: Optional[str] = None,
    k: int = 20,
    # top-level channels
    w_cf: float = 0.0,
    w_semantic: float = 1.0,
    embedder: Optional[Embedder] = None,
    # weights *inside* the semantic channel (seed vs query blend)
    w_sem_seed: float = 0.5,
    w_sem_query: float = 0.5,
    # internal hybrid (vector/text) used by the query channel
    hybrid_weight: float = 0.7,
    # optional filters (apply to the query channel only, to mirror /search/semantic)
    lang: str | None = None,
    fiction: bool | None = None,
    min_year: int | None = None,
    max_pages: int | None = None,
    exclude_rated_user_id: int | None = None,
) -> List[Tuple[Book, float, Dict[str, float]]]:
    """
    Merge CF + semantic signals into a final ranked list.
      - CF can combine user-CF and seed-by-ratings (optional).
      - Semantic is split into two subchannels: seed similarity & query hybrid search.
      - Each channel is min-max normalized; semantic subchannels are blended by w_sem_*.
      - Final score = w_cf * CF + w_semantic * SemanticCombined.
    Returns: [(Book, final_score, {"cf":..., "semantic":...})]
    """

    # collect channel scores
    cf_scores: Dict[int, float] = {}
    sem_seed: Dict[int, float] = {}
    sem_query: Dict[int, float] = {}

    # CF sources (optional - not using them yet)
    if user_id is not None:
        for bid, s in recommend_for_user(db, user_id=user_id, k=max(k * 3, 50)):
            cf_scores[bid] = cf_scores.get(bid, 0.0) + s
    if seed_book_id is not None:
        # treat similar-by-ratings to seed as CF-ish signal
        for bid, s in similar_books_by_ratings(db, seed_book_id, k=max(k * 3, 50)):
            cf_scores[bid] = max(cf_scores.get(bid, 0.0), s)

    # Semantic subchannels
    if seed_book_id is not None:
        for bid, s in semantic_similar_to_book(db, seed_book_id, k=max(k * 3, 100)):
            sem_seed[bid] = max(sem_seed.get(bid, 0.0), s)

    if query and embedder is not None:
        for bid, s in semantic_from_query_hybrid(
            db, embedder, query, k=max(k * 3, 100),
            hybrid_weight=hybrid_weight,
            lang=lang, fiction=fiction,
            min_year=min_year, max_pages=max_pages,
            exclude_rated_user_id=exclude_rated_user_id,
        ):
            sem_query[bid] = max(sem_query.get(bid, 0.0), s)

    # normalize each channel
    cf_n = _minmax_norm(cf_scores)
    sem_seed_n = _minmax_norm(sem_seed)
    sem_query_n = _minmax_norm(sem_query)

    # blend semantic subchannels explicitly (no max)
    sem_combined: Dict[int, float] = {}
    all_sem_ids = set(sem_seed_n) | set(sem_query_n)
    for bid in all_sem_ids:
        a = sem_seed_n.get(bid, 0.0)
        b = sem_query_n.get(bid, 0.0)
        sem_combined[bid] = (w_sem_seed * a) + (w_sem_query * b)

    # final blend with CF
    all_ids = set(cf_n) | set(sem_combined)
    if not all_ids:
        return []

    ranked: List[Tuple[int, float, Dict[str, float]]] = []
    for bid in all_ids:
        cf = cf_n.get(bid, 0.0)
        se = sem_combined.get(bid, 0.0)
        score = w_cf * cf + w_semantic * se
        ranked.append((bid, score, {"cf": cf, "semantic": se}))

    ranked.sort(key=lambda x: x[1], reverse=True)
    top = ranked[:k]

    # hydrate into Book rows
    book_map = fetch_books_by_ids(db, (bid for bid, _, _ in top))
    return [(book_map[bid], score, parts) for (bid, score, parts) in top if bid in book_map]
