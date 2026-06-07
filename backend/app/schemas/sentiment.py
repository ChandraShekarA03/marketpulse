from pydantic import BaseModel
from typing import List

class NewsArticle(BaseModel):
    headline: str
    url: str
    sentiment_label: str
    confidence: float

class SentimentResponse(BaseModel):
    ticker: str
    bullish_score: float
    bearish_score: float
    neutral_score: float
    market_sentiment: str
    articles_analyzed: int
    recent_news: List[NewsArticle]
