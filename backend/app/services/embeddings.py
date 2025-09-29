from typing import Iterable
from sqlalchemy import select, exists
from sqlalchemy.orm import Session
from sentence_transformers import SentenceTransformer

from ..models.book import Book
from ..models.embedding import Embedding

class Embedder:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    def encode_texts(self, texts: list[str]) -> list[list[float]]:
        # Default returns a NumPy array; some versions may return a Python list.
        vecs = self.model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True
        )
        # Ensure pure Python lists for SQLAlchemy/pgvector
        return vecs.tolist() if hasattr(vecs, "tolist") else vecs


def candidate_text(book: Book) -> str:
    bits = [book.title or ""]
    if getattr(book, "subtitle", None):
        bits.append(book.subtitle)
    return ": ".join([b for b in bits if b])


def iter_unembedded_books(db: Session) -> Iterable[Book]:
    # Books with no embedding row
    subq = select(Embedding.entity_id).where(Embedding.entity_type == "book")
    stmt = select(Book).where(~Book.id.in_(subq))
    return db.scalars(stmt)


def upsert_book_embeddings(db: Session, embedder: Embedder, batch_size: int = 256) -> tuple[int, int]:
    # Stream in batches to avoid loading everything
    total_candidates = 0
    inserted = 0

    while True:
        subq = select(Embedding.entity_id).where(Embedding.entity_type == "book")
        chunk_stmt = (
            select(Book)
            .where(~Book.id.in_(subq))
            .limit(batch_size)
        )
        books = list(db.scalars(chunk_stmt))
        if not books:
            break

        total_candidates += len(books)
        texts = [candidate_text(b) for b in books]
        vectors = embedder.encode_texts(texts)

        for b, v in zip(books, vectors):
            # merge() works like upsert for PK; here PK is (entity_type, entity_id)
            db.merge(Embedding(entity_type="book", entity_id=b.id, vector=v))
        db.commit()
        inserted += len(books)

    return total_candidates, inserted
