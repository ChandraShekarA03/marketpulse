from fastapi import APIRouter
from app.services.sentiment_service import analyze_sentiment
from app.schemas.sentiment import SentimentResponse

router = APIRouter(
    prefix="/sentiment",
    tags=["Sentiment"]
)

@router.get("/{ticker}", response_model=SentimentResponse)
def get_sentiment(ticker: str):
    """
    Fetch recent financial news for a ticker and perform sentiment analysis using FinBERT.
    Returns aggregated bullish, bearish, and neutral scores.
    """
    return analyze_sentiment(ticker)
