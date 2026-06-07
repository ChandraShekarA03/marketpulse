from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class HoldingCreate(BaseModel):
    ticker: str
    shares: float
    average_buy_price: float

class HoldingResponse(BaseModel):
    id: int
    portfolio_id: int
    ticker: str
    shares: float
    average_buy_price: float
    added_at: datetime
    
    # Live fields populated dynamically
    current_price: Optional[float] = None
    profit_loss: Optional[float] = None
    allocation_percentage: Optional[float] = None

    class Config:
        from_attributes = True

class PortfolioCreate(BaseModel):
    name: str

class PortfolioResponse(BaseModel):
    id: int
    name: str
    user_id: int
    created_at: datetime
    holdings: List[HoldingResponse] = []
    
    # Analytics
    total_value: Optional[float] = None
    total_profit_loss: Optional[float] = None
    risk_score: Optional[float] = None

    class Config:
        from_attributes = True
