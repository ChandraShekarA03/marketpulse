import logging
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk
from app.rag.embeddings import create_embedding

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None

logger = logging.getLogger(__name__)


def _build_source_item(chunk: DocumentChunk) -> Dict[str, str]:
    return {
        "filing_type": chunk.document.filing_type,
        "filing_date": chunk.document.filing_date.isoformat() if chunk.document.filing_date else "",
        "source_url": chunk.document.source_url,
        "chunk_index": chunk.chunk_index,
        "snippet": chunk.chunk_text[:300],
    }


async def retrieve_relevant_chunks(
    db: Session,
    ticker: str,
    question: str,
    top_k: int = 4,
) -> List[Dict[str, str]]:
    ticker = ticker.upper().strip()
    query_embedding = await create_embedding(question)

    if Vector is None:
        raise RuntimeError("pgvector is required for RAG retrieval. Install the pgvector package.")

    chunks = (
        db.query(DocumentChunk)
        .join(Document)
        .filter(Document.ticker == ticker)
        .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
        .limit(top_k)
        .all()
    )

    return [
        {
            "chunk_text": chunk.chunk_text,
            "filing_type": chunk.document.filing_type,
            "filing_date": chunk.document.filing_date.isoformat() if chunk.document.filing_date else "",
            "source_url": chunk.document.source_url,
            "chunk_index": chunk.chunk_index,
        }
        for chunk in chunks
    ]


def has_rag_context(db: Session, ticker: str) -> bool:
    ticker = ticker.upper().strip()
    return db.query(Document).filter(Document.ticker == ticker).count() > 0
