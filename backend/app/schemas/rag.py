from pydantic import BaseModel
from typing import List, Optional

class RagIngestResponse(BaseModel):
    documents_ingested: int
    chunks_ingested: int
    message: Optional[str] = None


class RagQueryRequest(BaseModel):
    ticker: str
    question: str


class RagSource(BaseModel):
    source_url: str
    filing_type: str
    filing_date: str


class RagQueryResponse(BaseModel):
    answer: str
    sources: List[RagSource]
    citations: List[str]
