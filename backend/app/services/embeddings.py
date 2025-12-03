from __future__ import annotations
import os
from typing import Iterable, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from app.models.book import Book
from app.models.embedding import Embedding

load_dotenv()

EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
EMBED_DIM = int(os.getenv("EMBED_DIM", "384"))
EMBED_PROVIDER = os.getenv("EMBED_PROVIDER", "fastembed").lower()  # "fastembed" (default) or "sentence-transformers"
MAX_DESC_CHARS = 4000

def _is_bge(model_name: str) -> bool:
    return "bge" in (model_name or "").lower()


class Embedder:
    """
    Pluggable embedder:
      - PROD default: FastEmbed (small, no torch)
      - LOCAL heavy: SentenceTransformers (torch) when EMBED_PROVIDER=sentence-transformers

    Public API:
      - encode_docs(List[str]) -> List[List[float]]
      - encode_query(str) -> List[float]
    """

    def __init__(self, model_name: Optional[str] = None, provider: Optional[str] = None):
        self.model_name = model_name or EMBED_MODEL
        self.provider = (provider or EMBED_PROVIDER).lower()

        if self.provider == "sentence-transformers":
            # Lazy import so prod images don’t pull torch
            from sentence_transformers import SentenceTransformer  # type: ignore
            self._backend = "st"
            self._model = SentenceTransformer(self.model_name)
        else:
            # Default lightweight backend
            from fastembed import TextEmbedding  # type: ignore
            self._backend = "fastembed"
            self._model = TextEmbedding(self.model_name)

    # Internal helpers
    def _prep_doc(self, t: str) -> str:
        if _is_bge(self.model_name):
            # bge doc instruction
            return f"Represent this passage for retrieval: {t}"
        return t

    def _prep_query(self, q: str) -> str:
        if _is_bge(self.model_name):
            # bge query instruction
            return f"Represent this query for retrieving relevant passages: {q}"
        return q

    # Public API
    def encode_docs(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        texts = [self._prep_doc(t or "") for t in texts]

        if self._backend == "st":
            # SentenceTransformers returns np array; normalize_embeddings=True helps cosine
            return (
                self._model.encode(  # type: ignore[attr-defined]
                    texts,
                    normalize_embeddings=True,
                    convert_to_numpy=True,
                    show_progress_bar=False,
                ).tolist()
            )
        else:
            # FastEmbed returns a generator of np arrays
            return [v.tolist() for v in self._model.embed(texts)]  # type: ignore[attr-defined]

    def encode_query(self, q: str) -> List[float]:
        q = (q or "").strip()
        if not q:
            return []

        q = self._prep_query(q)

        if self._backend == "st":
            return (
                self._model.encode(  # type: ignore[attr-defined]
                    [q],
                    normalize_embeddings=True,
                    convert_to_numpy=True,
                    show_progress_bar=False,
                )[0].tolist()
            )
        else:
            return next(self._model.embed([q])).tolist()  # type: ignore[attr-defined]


def _book_to_text(b: Book) -> str:
    parts: List[str] = []
    if b.title:
        parts.append(b.title)
    if getattr(b, "author", None):
        parts.append(b.author)
    if getattr(b, "description", None):
        parts.append((b.description or "")[:MAX_DESC_CHARS])
    return ". ".join([p.strip() for p in parts if p and str(p).strip()])

def _books_to_embed(db: Session) -> Iterable[Book]:
    return db.scalars(select(Book))

def upsert_book_embeddings(db: Session, embedder: Embedder, batch: int = 256) -> Tuple[int, int]:
    rows = list(_books_to_embed(db))
    docs = [_book_to_text(b) or (b.title or "") for b in rows]
    seen, inserted = len(rows), 0
    for i in range(0, seen, batch):
        chunk = rows[i : i + batch]
        vecs = embedder.encode_docs(docs[i : i + batch])
        for b, v in zip(chunk, vecs):
            db.merge(Embedding(entity_type="book", entity_id=b.id, vector=v))
        db.commit()
        inserted += len(chunk)
    return seen, inserted
