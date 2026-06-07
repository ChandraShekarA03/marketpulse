from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_active_user, get_db
from app.agents.schema import QueryRequest
from app.agents.agent_service import stream_enterprise_analysis
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["Agent"])

@router.post("/analyze")
async def analyze(request: QueryRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """
    Stream enterprise AI Analyst output for a user financial query.
    """
    try:
        logger.info(f"Agent received query: {request.query} for user {current_user.id}")
        generator = await stream_enterprise_analysis(db, current_user, request.query)
        return StreamingResponse(generator, media_type="text/plain")
    except ValueError as e:
        logger.error(f"Value error in agent execution: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Agent analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Agent analysis failed: {str(e)}")
