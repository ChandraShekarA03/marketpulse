from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    company = Column(String, index=True, nullable=False)
    ticker = Column(String, index=True, nullable=False)
    filing_type = Column(String, index=True, nullable=False)
    filing_date = Column(DateTime, nullable=False)
    source_url = Column(String, unique=True, nullable=False)
    document_metadata = Column("metadata", Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False, default=0, index=True)

    if Vector is not None:
        embedding = Column(Vector(1536), nullable=False)
    else:
        embedding = Column(Text, nullable=True)

    document = relationship("Document", back_populates="chunks")
