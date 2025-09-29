from pathlib import Path
import os

from sqlalchemy import create_engine, text

SQL_PATH = Path(__file__).with_name("migrations") / "20250928_add_pgvector_embeddings.sql"
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

sql_text = SQL_PATH.read_text()

with engine.begin() as conn:
    # Enable extension + create table + index (idempotent)
    for stmt in sql_text.split(";"):
        s = stmt.strip()
        if s:
            conn.execute(text(s))
print("Migration applied: pgvector + embeddings table")
