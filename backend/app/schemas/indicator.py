from pydantic import BaseModel
from typing import Dict, Any, Optional

class IndicatorValues(BaseModel):
    RSI: Optional[float] = None
    MACD: Optional[float] = None
    MACD_signal: Optional[float] = None
    MACD_hist: Optional[float] = None
    SMA20: Optional[float] = None
    EMA50: Optional[float] = None
    BB_high: Optional[float] = None
    BB_low: Optional[float] = None
    ATR: Optional[float] = None
    Stochastic_k: Optional[float] = None
    Stochastic_d: Optional[float] = None

class IndicatorResponse(BaseModel):
    ticker: str
    latest_close: float
    indicators: IndicatorValues
    trend: str
    signal: str
