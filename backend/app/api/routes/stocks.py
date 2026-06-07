from fastapi import APIRouter
from app.services.stock_service import get_stock_data
from app.schemas.stock import StockResponse

router = APIRouter(
    prefix="/stocks",
    tags=["Stocks"]
)

@router.get("/{ticker}", response_model=StockResponse)
def fetch_stock(ticker: str):
    """
    Fetch real-time stock data for a given ticker symbol.
    Data is cached for 5 minutes.
    """
    # The get_stock_data service returns a dict that will be validated and serialized by StockResponse
    return get_stock_data(ticker.upper())