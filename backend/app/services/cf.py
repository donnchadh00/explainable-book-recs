from __future__ import annotations
from collections import defaultdict
from typing import Dict, Iterable, List, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.book import Book
from app.models.rating import Rating


# Low-level: pull ratings
def _all_ratings(db: Session) -> List[Tuple[int, int, float]]:
    """
    Return [(user_id, book_id, rating), ...]
    """
    rows = db.execute(
        select(Rating.user_id, Rating.book_id, Rating.rating)
    ).all()
    return [(u, b, float(r)) for (u, b, r) in rows if r is not None]


def _user_ratings_map(db: Session) -> Dict[int, Dict[int, float]]:
    """
    user_id -> {book_id: rating}
    """
    by_user: Dict[int, Dict[int, float]] = defaultdict(dict)
    for u, b, r in _all_ratings(db):
        by_user[u][b] = r
    return by_user


def _item_users_map(db: Session) -> Dict[int, Dict[int, float]]:
    """
    book_id -> {user_id: rating}
    """
    by_item: Dict[int, Dict[int, float]] = defaultdict(dict)
    for u, b, r in _all_ratings(db):
        by_item[b][u] = r
    return by_item


# Math helpers
def _cosine(vec_a: Dict[int, float], vec_b: Dict[int, float]) -> float:
    """
    Cosine similarity between two sparse dict vectors sharing keys = user_ids (for item-item)
    """
    # intersection of keys
    common = set(vec_a.keys()) & set(vec_b.keys())
    if not common:
        return 0.0
    dot = sum(vec_a[u] * vec_b[u] for u in common)
    na = sum(v * v for v in vec_a.values()) ** 0.5
    nb = sum(v * v for v in vec_b.values()) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


# Public: similar-by-ratings
def similar_books_by_ratings(db: Session, book_id: int, k: int = 10, min_overlap: int = 2) -> List[Tuple[int, float]]:
    """
    Item-item similarity using user rating vectors.
    Returns [(other_book_id, sim_score)] sorted desc.
    min_overlap: require at least n shared raters to consider similarity > 0
    """
    item_users = _item_users_map(db)
    target = item_users.get(book_id, {})
    if not target:
        return []

    sims: List[Tuple[int, float]] = []
    for other_id, other_vec in item_users.items():
        if other_id == book_id:
            continue
        # fast overlap check
        overlap = len(set(target.keys()) & set(other_vec.keys()))
        if overlap < min_overlap:
            continue
        sims.append((other_id, _cosine(target, other_vec)))

    sims.sort(key=lambda x: x[1], reverse=True)
    return sims[:k]


# Public: recommend for a user
def recommend_for_user(db: Session, user_id: int, k: int = 10, min_overlap: int = 2) -> List[Tuple[int, float]]:
    """
    Recommend items for a user using weighted sum of item-item similarities:
      score(candidate) = sum_{rated item i} sim(candidate, i) * rating(user, i)
    Excludes books already rated by the user.
    """
    by_user = _user_ratings_map(db)
    item_users = _item_users_map(db)

    ur = by_user.get(user_id, {})
    if not ur:
        return []

    # Precompute similarities from each rated item to all others (lazy, local)
    scores: Dict[int, float] = defaultdict(float)
    for rated_book_id, r in ur.items():
        target = item_users.get(rated_book_id, {})
        if not target:
            continue
        for other_id, other_vec in item_users.items():
            if other_id in ur or other_id == rated_book_id:
                continue
            # overlap gate
            overlap = len(set(target.keys()) & set(other_vec.keys()))
            if overlap < min_overlap:
                continue
            sim = _cosine(target, other_vec)
            if sim <= 0:
                continue
            scores[other_id] += sim * r

    # Top-K
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return ranked[:k]


# Convenience: hydrate ids to book rows
def fetch_books_by_ids(db: Session, ids: Iterable[int]) -> Dict[int, Book]:
    if not ids:
        return {}
    id_list = list(set(ids))
    rows = db.execute(select(Book).where(Book.id.in_(id_list))).scalars().all()
    return {b.id: b for b in rows}


# Example manual run:
# with SessionLocal() as db:
#     print(similar_books_by_ratings(db, book_id=123, k=10))
#     print(recommend_for_user(db, user_id=1, k=10))
