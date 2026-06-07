from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.dependencies import get_db, get_current_active_user
from app.schemas.rag import RagIngestResponse, RagQueryRequest, RagQueryResponse
from app.rag.services import query_company_rag
from app.rag.ingestion import ingest_filings
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["RAG"])

@router.post("/ingest/{ticker}", response_model=RagIngestResponse)
async def ingest_filings_route(
    ticker: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        result = await ingest_filings(db, ticker)
        return RagIngestResponse(
            documents_ingested=result["documents_ingested"],
            chunks_ingested=result["chunks_ingested"],
            message=f"Ingested filings for {ticker}."
        )
    except ValueError as e:
        logger.warning(f"RAG ingest validation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"RAG ingest failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to ingest SEC filings.")


@router.post("/query", response_model=RagQueryResponse)
async def query_rag_route(
    request: RagQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        result = await query_company_rag(db, request.ticker, request.question)
        return RagQueryResponse(**result)
    except Exception as e:
        logger.error(f"RAG query failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve research answer.")
