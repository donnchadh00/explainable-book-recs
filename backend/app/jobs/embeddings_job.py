from __future__ import annotations
import os

from app.db import SessionLocal
from app.services.embeddings import Embedder, upsert_book_embeddings

MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")

if __name__ == "__main__":
    embedder = Embedder(MODEL)
    with SessionLocal() as db:
        seen, inserted = upsert_book_embeddings(db, embedder)
        print(f"Embeddings upserted — candidates: {seen}, inserted: {inserted}")
