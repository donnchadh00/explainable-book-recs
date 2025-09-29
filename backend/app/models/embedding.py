from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, BigInteger
from pgvector.sqlalchemy import Vector
from ..db import Base

class Embedding(Base):
    __tablename__ = "embeddings"

    entity_type: Mapped[str] = mapped_column(String, primary_key=True)
    entity_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    vector: Mapped[list[float]] = mapped_column(Vector(384), nullable=False)
