import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from fastapi import HTTPException
from datetime import datetime
from app.core.config import settings
from app.services.cache_service import cache_response
import logging

logger = logging.getLogger(__name__)

# Configure a session with retry logic
session = requests.Session()
retry = Retry(
    total=3,
    read=3,
    connect=3,
    backoff_factor=0.3,
    status_forcelist=[429, 500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retry)
session.mount("http://", adapter)
session.mount("https://", adapter)

@cache_response(ttl_seconds=300) # 5 minutes cache
def get_stock_data(ticker: str) -> dict:
    """
    Fetch real-time stock data from AlphaVantage.
    Uses retry logic and caches the successful response for 5 minutes.
    """
    try:
        url = (
            f"https://www.alphavantage.co/query"
            f"?function=GLOBAL_QUOTE"
            f"&symbol={ticker}"
            f"&apikey={settings.ALPHA_VANTAGE_API_KEY}"
        )

        response = session.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Handle API rate limits or errors from AlphaVantage
        if "Information" in data or "Note" in data:
            raise HTTPException(
                status_code=429,
                detail="AlphaVantage API rate limit reached or invalid API key."
            )

        quote = data.get("Global Quote")
        
        if not quote or "05. price" not in quote:
            raise HTTPException(
                status_code=404,
                detail=f"Stock data not found for ticker: {ticker}"
            )

        # Map to Pydantic schema structure
        result = {
            "symbol": quote["01. symbol"],
            "price": float(quote["05. price"]),
            "open": float(quote["02. open"]),
            "high": float(quote["03. high"]),
            "low": float(quote["04. low"]),
            "volume": int(quote["06. volume"]),
            "timestamp": datetime.now().isoformat(),
            "previous_close": float(quote["08. previous close"])
        }
        return result

    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed for {ticker}: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="Stock data provider is currently unavailable."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching data for {ticker}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while fetching stock data."
        )

@cache_response(ttl_seconds=3600) # 1 hour cache for historical data
def get_historical_data(ticker: str, outputsize: str = "compact") -> list:
    """
    Fetch historical daily stock data from AlphaVantage.
    outputsize: "compact" (latest 100 data points) or "full" (20+ years of historical data)
    """
    try:
        url = (
            f"https://www.alphavantage.co/query"
            f"?function=TIME_SERIES_DAILY"
            f"&symbol={ticker}"
            f"&outputsize={outputsize}"
            f"&apikey={settings.ALPHA_VANTAGE_API_KEY}"
        )

        response = session.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()

        if "Information" in data or "Note" in data:
            raise HTTPException(
                status_code=429,
                detail="AlphaVantage API rate limit reached or invalid API key."
            )

        time_series = data.get("Time Series (Daily)")
        
        if not time_series:
            raise HTTPException(
                status_code=404,
                detail=f"Historical data not found for ticker: {ticker}"
            )

        # Parse into a flat list of dictionaries
        historical_data = []
        for date_str, values in time_series.items():
            historical_data.append({
                "date": date_str,
                "open": float(values["1. open"]),
                "high": float(values["2. high"]),
                "low": float(values["3. low"]),
                "close": float(values["4. close"]),
                "volume": int(values["5. volume"])
            })

        # Sort chronological (oldest to newest) - useful for technical analysis
        historical_data.sort(key=lambda x: x["date"])
        return historical_data

    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed for historical data {ticker}: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="Stock data provider is currently unavailable."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching historical data for {ticker}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while fetching historical stock data."
        )