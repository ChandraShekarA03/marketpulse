from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class QueryRequest(BaseModel):
    query: str

class AgentResponse(BaseModel):
    symbol: str
    recommendation: str
    confidence: int
    reasoning: List[str]
    data: Dict[str, Any]
