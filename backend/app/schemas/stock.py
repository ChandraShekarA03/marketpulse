from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class StockResponse(BaseModel):
    symbol: str
    price: float
    open: float
    high: float
    low: float
    volume: int
    timestamp: datetime
    previous_close: Optional[float] = None

class StockError(BaseModel):
    detail: str
