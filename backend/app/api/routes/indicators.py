from fastapi import APIRouter
from app.services.indicator_service import generate_indicators
from app.schemas.indicator import IndicatorResponse

router = APIRouter(
    prefix="/indicators",
    tags=["Indicators"]
)

@router.get("/{ticker}", response_model=IndicatorResponse)
def get_technical_indicators(ticker: str):
    """
    Generate technical indicators for a given stock using historical data.
    Includes RSI, MACD, SMA20, EMA50, Bollinger Bands, ATR, Stochastic Oscillator.
    Also provides a trend interpretation and a buy/sell/neutral signal.
    """
    return generate_indicators(ticker)
