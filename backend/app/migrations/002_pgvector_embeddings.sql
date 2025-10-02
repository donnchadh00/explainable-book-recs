-- Enable extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Embeddings table
CREATE TABLE IF NOT EXISTS embeddings (
  entity_type TEXT NOT NULL CHECK (entity_type IN ('book')),
  entity_id   BIGINT NOT NULL,
  vector      VECTOR(384) NOT NULL,
  PRIMARY KEY (entity_type, entity_id)
);

-- ANN index
CREATE INDEX IF NOT EXISTS idx_embeddings_vector_cosine
  ON embeddings USING ivfflat (vector vector_cosine_ops) WITH (lists = 100);

-- do NOT fail if books not there yet on old DBs
DO $$
BEGIN
  IF to_regclass('public.books') IS NOT NULL AND
     NOT EXISTS (
       SELECT 1 FROM pg_constraint
       WHERE conname = 'fk_embeddings_book'
     ) THEN
    ALTER TABLE embeddings
      ADD CONSTRAINT fk_embeddings_book
      FOREIGN KEY (entity_id) REFERENCES books(id)
      DEFERRABLE INITIALLY DEFERRED;
  END IF;
END$$;
