from fastapi import APIRouter, Query
from app.services.prediction_service import run_prediction
from app.schemas.prediction import PredictionResponse

router = APIRouter(
    prefix="/predict",
    tags=["Prediction"]
)

@router.get("/{ticker}", response_model=PredictionResponse)
def get_prediction(
    ticker: str, 
    model: str = Query(..., description="Model to use: linear, randomforest, xgboost, lstm")
):
    """
    Run machine learning prediction for a given stock ticker.
    Supports Linear Regression, Random Forest, XGBoost, and LSTM.
    Includes feature engineering and sequence modeling for LSTM.
    Returns predicted next day close, trend, confidence score, and metrics.
    """
    return run_prediction(ticker, model)
