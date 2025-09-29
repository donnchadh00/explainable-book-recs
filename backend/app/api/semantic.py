from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text, bindparam
from sqlalchemy.orm import Session
from sentence_transformers import SentenceTransformer
from pgvector.sqlalchemy import Vector
from ..db import get_db

router = APIRouter(prefix="/search", tags=["search"])
_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

@router.get("/semantic")
def semantic_search(
    q: str,
    k: int = 20,
    exclude_rated_user_id: int | None = None,
    db: Session = Depends(get_db),
):
    if not q.strip():
        raise HTTPException(400, detail="Query 'q' is required")

    # normalized vector
    qvec = _model.encode([q], normalize_embeddings=True, convert_to_numpy=True)[0].tolist()

    base_sql = """
        SELECT b.id, b.title, b.published_year, b.page_count,
               1 - (e.vector <=> :qvec) AS cosine
        FROM embeddings e
        JOIN books b ON b.id = e.entity_id
        WHERE e.entity_type = 'book'
    """

    if exclude_rated_user_id is not None:
        base_sql += """
            AND NOT EXISTS (
              SELECT 1 FROM ratings r
              WHERE r.book_id = b.id AND r.user_id = :uid
            )
        """

    base_sql += """
        ORDER BY e.vector <=> :qvec
        LIMIT :k
    """

    stmt = text(base_sql).bindparams(
        bindparam("qvec", type_=Vector(384)),
    )

    params = {"qvec": qvec, "k": k}
    if exclude_rated_user_id is not None:
        params["uid"] = exclude_rated_user_id

    rows = db.execute(stmt, params).mappings().all()
    # round cosine similarity for display
    results = [{**dict(r), "cosine": float(f"{r['cosine']:.6f}")} for r in rows]
    return {"query": q, "k": k, "results": results}
