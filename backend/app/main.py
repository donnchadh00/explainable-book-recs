from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import os
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db import engine, get_db, Base
from app import models
from app.api.books import router as books_router

app = FastAPI(title="Book Recs API")

# Create tables at startup (simple MVP; later use Alembic)
Base.metadata.create_all(bind=engine)

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(books_router)

@app.get("/")
def root():
    return {"message": "Book Recs API is up. Try /health or /db-ping or /docs."}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/db-ping")
def db_ping(db: Session = Depends(get_db)):
    version = db.execute(text("select version()")).scalar()
    return {"db": "ok", "version": version}
