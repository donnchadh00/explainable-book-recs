from __future__ import annotations
import os
from typing import Iterable, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session
from sentence_transformers import SentenceTransformer

from app.models.book import Book
from app.models.embedding import Embedding
from dotenv import load_dotenv

load_dotenv()

EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
EMBED_DIM = int(os.getenv("EMBED_DIM", "384"))
MAX_DESC_CHARS = 4000

def _is_bge(model_name: str) -> bool:
    return "bge" in model_name.lower()

class Embedder:
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or EMBED_MODEL
        self.model = SentenceTransformer(self.model_name)

    def encode_docs(self, texts: List[str]) -> List[List[float]]:
        if _is_bge(self.model_name):
            texts = [f"Represent this passage for retrieval: {t}" for t in texts]
        return self.model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        ).tolist()

    def encode_query(self, q: str) -> List[float]:
        if _is_bge(self.model_name):
            q = f"Represent this query for retrieving relevant passages: {q}"
        return self.model.encode(
            [q],
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )[0].tolist()

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
        chunk = rows[i:i+batch]
        vecs = embedder.encode_docs(docs[i:i+batch])
        for b, v in zip(chunk, vecs):
            db.merge(Embedding(entity_type="book", entity_id=b.id, vector=v))
        db.commit()
        inserted += len(chunk)
    return seen, inserted
