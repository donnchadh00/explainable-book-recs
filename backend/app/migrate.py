import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import text, create_engine

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
assert DATABASE_URL, "DATABASE_URL not set"

MIGRATIONS_DIR = Path(__file__).with_name("migrations")

engine = create_engine(DATABASE_URL, future=True)

def run():
    files = sorted(p for p in MIGRATIONS_DIR.glob("*.sql"))
    if not files:
        print("No migrations found.")
        return
    with engine.begin() as conn:
        for f in files:
            sql = f.read_text()
            conn.execute(text(sql))
            print(f"Applied {f.name}")

if __name__ == "__main__":
    run()
