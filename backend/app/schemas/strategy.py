from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class StrategyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    rules_json: Dict[str, Any]


class StrategyGenerateRequest(BaseModel):
    prompt: str
    name: Optional[str] = None


class StrategyResponse(BaseModel):
    id: int
    user_id: int
    name: str
    description: Optional[str] = None
    rules_json: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


class StrategyAIResponse(StrategyResponse):
    risk_profile: Optional[str] = None
    reasoning: Optional[str] = None


class StrategyListResponse(BaseModel):
    strategies: List[StrategyResponse]

    class Config:
        from_attributes = True
