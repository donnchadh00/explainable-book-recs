from __future__ import annotations
import hashlib
import os
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import text, create_engine

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
assert DATABASE_URL, "DATABASE_URL not set"

MIGRATIONS_DIR = Path(__file__).with_name("migrations")
engine = create_engine(DATABASE_URL, future=True)

def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def ensure_schema_table(conn):
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
          id SERIAL PRIMARY KEY,
          filename TEXT NOT NULL UNIQUE,
          checksum TEXT NOT NULL,
          applied_at TIMESTAMP NOT NULL DEFAULT now()
        )
    """))

def already_applied(conn, filename: str) -> bool:
    return bool(conn.execute(
        text("SELECT 1 FROM schema_migrations WHERE filename = :f"),
        {"f": filename}
    ).scalar())

def record_applied(conn, filename: str, checksum: str):
    conn.execute(
        text("INSERT INTO schema_migrations (filename, checksum, applied_at) VALUES (:f, :c, :t)"),
        {"f": filename, "c": checksum, "t": datetime.utcnow()}
    )

def run():
    files = sorted(p for p in MIGRATIONS_DIR.glob("*.sql"))
    if not files:
        print("No migrations found.")
        return

    with engine.begin() as conn:
        ensure_schema_table(conn)

        for f in files:
            filename = f.name
            sql = f.read_text()
            if already_applied(conn, filename):
                print(f"Skip {filename} (already applied)")
                continue

            conn.execute(text(sql))
            record_applied(conn, filename, sha256(sql))
            print(f"Applied {filename}")

    print("All migrations up to date.")

if __name__ == "__main__":
    run()
