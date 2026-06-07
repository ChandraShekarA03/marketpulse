from pydantic import BaseModel
from typing import Dict

class EvaluationMetrics(BaseModel):
    MAE: float
    MSE: float
    RMSE: float
    R2: float

class PredictionResponse(BaseModel):
    ticker: str
    model: str
    today_price: float
    predicted_next_day: float
    trend: str
    confidence_score: float
    evaluation_metrics: EvaluationMetrics
