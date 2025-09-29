import os
from ..db import SessionLocal
from ..services.embeddings import Embedder, upsert_book_embeddings

MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

if __name__ == "__main__":
    embedder = Embedder(MODEL)
    with SessionLocal() as db:
        seen, inserted = upsert_book_embeddings(db, embedder)
        print(f"Embeddings upserted — candidates: {seen}, inserted: {inserted}")
