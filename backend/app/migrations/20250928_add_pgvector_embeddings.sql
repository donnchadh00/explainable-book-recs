-- Enable extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Embeddings table (book-only for now)
CREATE TABLE IF NOT EXISTS embeddings (
entity_type TEXT NOT NULL CHECK (entity_type IN ('book')),
entity_id BIGINT NOT NULL,
vector VECTOR(384) NOT NULL,
PRIMARY KEY (entity_type, entity_id)
);

-- ANN index for cosine search
CREATE INDEX IF NOT EXISTS idx_embeddings_vector_cosine
ON embeddings USING ivfflat (vector vector_cosine_ops) WITH (lists = 100);

-- Helpful FK (for referential hygiene)
ALTER TABLE embeddings
ADD CONSTRAINT fk_embeddings_book
FOREIGN KEY (entity_id) REFERENCES books(id)
DEFERRABLE INITIALLY DEFERRED;
