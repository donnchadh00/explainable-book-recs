from sqlalchemy import Column, Integer, BigInteger, Float, Text, DateTime, PrimaryKeyConstraint
from app.db import Base

class Rating(Base):
    __tablename__ = "ratings"
    user_id = Column(Integer, nullable=False, default=1)
    book_id = Column(BigInteger, nullable=False)
    rating = Column(Float)
    rated_at = Column(DateTime)
    source = Column(Text, default="goodreads")

    __table_args__ = (PrimaryKeyConstraint("user_id", "book_id"),)
