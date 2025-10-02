from sqlalchemy import Column, BigInteger, Integer, Text
from app.db import Base

class Book(Base):
    __tablename__ = "books"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    title = Column(Text, nullable=False)
    author = Column(Text)
    published_year = Column(Integer)
    isbn13 = Column(Text, unique=True)
    page_count = Column(Integer)
    description = Column(Text, nullable=True)
