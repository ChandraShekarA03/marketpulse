import os
import requests
import datetime
from fastapi import HTTPException
from app.core.config import settings
from app.services.cache_service import cache_response
import logging

# Only load transformers if available (can be heavy)
try:
    from transformers import pipeline
    # Load FinBERT
    # In a real production scenario, this model would be loaded once globally or in a Celery worker.
    # For demonstration, we initialize it if transformers is available.
    sentiment_pipeline = pipeline("sentiment-analysis", model="ProsusAI/finbert")
    TRANSFORMERS_AVAILABLE = True
except Exception:
    TRANSFORMERS_AVAILABLE = False
    sentiment_pipeline = None

logger = logging.getLogger(__name__)

def fetch_company_news(ticker: str) -> list:
    """
    Fetch recent company news using Finnhub API.
    """
    # If no API key, return mock data to prevent blocking
    if not settings.FINNHUB_API_KEY or settings.FINNHUB_API_KEY == "demo":
        return [
            {"headline": f"{ticker} announces record breaking profits this quarter.", "url": "https://example.com/1"},
            {"headline": f"Investors are worried about {ticker}'s new supply chain issues.", "url": "https://example.com/2"},
            {"headline": f"{ticker} stock remains stable ahead of earnings call.", "url": "https://example.com/3"}
        ]
        
    try:
        # Fetch news for the last 7 days
        today = datetime.date.today()
        last_week = today - datetime.timedelta(days=7)
        
        url = (
            f"https://finnhub.io/api/v1/company-news"
            f"?symbol={ticker}"
            f"&from={last_week.strftime('%Y-%m-%d')}"
            f"&to={today.strftime('%Y-%m-%d')}"
            f"&token={settings.FINNHUB_API_KEY}"
        )
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        return [{"headline": item["headline"], "url": item["url"]} for item in data[:10]]
        
    except Exception as e:
        logger.error(f"Failed to fetch news for {ticker}: {e}")
        return []

@cache_response(ttl_seconds=3600) # Cache for 1 hour to save API calls and compute
def analyze_sentiment(ticker: str) -> dict:
    news_items = fetch_company_news(ticker)
    
    if not news_items:
        raise HTTPException(status_code=404, detail=f"No recent news found for {ticker}.")

    headlines = [item["headline"] for item in news_items]
    
    analyzed_articles = []
    bullish_count = 0
    bearish_count = 0
    neutral_count = 0
    
    if TRANSFORMERS_AVAILABLE and sentiment_pipeline:
        try:
            results = sentiment_pipeline(headlines)
            
            for item, result in zip(news_items, results):
                label = result["label"].lower() # FinBERT outputs positive, negative, neutral
                score = result["score"]
                
                # Map FinBERT labels to market terminology
                if label == "positive":
                    market_label = "bullish"
                    bullish_count += 1
                elif label == "negative":
                    market_label = "bearish"
                    bearish_count += 1
                else:
                    market_label = "neutral"
                    neutral_count += 1
                    
                analyzed_articles.append({
                    "headline": item["headline"],
                    "url": item["url"],
                    "sentiment_label": market_label,
                    "confidence": float(score)
                })
        except Exception as e:
            logger.error(f"FinBERT prediction failed: {e}")
            raise HTTPException(status_code=500, detail="Sentiment analysis model failed.")
    else:
        # Fallback if transformers not installed
        for item in news_items:
            # Dummy analysis
            market_label = "neutral"
            neutral_count += 1
            analyzed_articles.append({
                "headline": item["headline"],
                "url": item["url"],
                "sentiment_label": market_label,
                "confidence": 0.5
            })

    total = max(len(analyzed_articles), 1)
    bullish_score = (bullish_count / total) * 100
    bearish_score = (bearish_count / total) * 100
    neutral_score = (neutral_count / total) * 100
    
    if bullish_score > bearish_score and bullish_score > 40:
        overall_sentiment = "BULLISH"
    elif bearish_score > bullish_score and bearish_score > 40:
        overall_sentiment = "BEARISH"
    else:
        overall_sentiment = "NEUTRAL"
        
    return {
        "ticker": ticker.upper(),
        "bullish_score": round(bullish_score, 2),
        "bearish_score": round(bearish_score, 2),
        "neutral_score": round(neutral_score, 2),
        "market_sentiment": overall_sentiment,
        "articles_analyzed": total,
        "recent_news": analyzed_articles
    }
