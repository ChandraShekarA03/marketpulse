from datetime import date, datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class BacktestRunCreate(BaseModel):
    strategy_id: int
    ticker: str
    start_date: date
    end_date: date


class BacktestOptimizeRequest(BaseModel):
    strategy_id: int
    ticker: str
    start_date: date
    end_date: date
    parameter: str
    lower_bound: float
    upper_bound: float
    step: float = Field(default=1.0, gt=0.0)


class BacktestRunResponse(BaseModel):
    id: int
    strategy_id: int
    ticker: str
    start_date: date
    end_date: date
    results_json: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


class BacktestOptimizationResult(BaseModel):
    best_by_sharpe: Dict[str, Any]
    best_by_return: Dict[str, Any]
    best_by_drawdown: Dict[str, Any]
    parameter: str
    parameter_values_tested: int
