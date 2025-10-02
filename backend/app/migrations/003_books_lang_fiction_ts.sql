ALTER TABLE books
  ADD COLUMN IF NOT EXISTS language_code TEXT,
  ADD COLUMN IF NOT EXISTS is_fiction BOOLEAN;

-- Generated tsvector for BM25 ranking
ALTER TABLE books
  ADD COLUMN IF NOT EXISTS ts tsvector
  GENERATED ALWAYS AS (
    to_tsvector(
      'english',
      coalesce(title,'') || ' ' || coalesce(description,'')
    )
  ) STORED;

CREATE INDEX IF NOT EXISTS idx_books_ts ON books USING GIN (ts);
