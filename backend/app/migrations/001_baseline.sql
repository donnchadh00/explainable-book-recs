CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  display_name TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'local'
);

CREATE TABLE IF NOT EXISTS books (
  id BIGSERIAL PRIMARY KEY,
  title TEXT NOT NULL,
  author TEXT,
  published_year INT,
  isbn13 TEXT UNIQUE,
  page_count INT,
  description TEXT
);

CREATE TABLE IF NOT EXISTS ratings (
  user_id INT REFERENCES users(id),
  book_id BIGINT REFERENCES books(id),
  rating REAL CHECK (rating BETWEEN 0 AND 5),
  rated_at TIMESTAMP,
  source TEXT,
  PRIMARY KEY (user_id, book_id)
);
