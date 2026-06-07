"""Schemas for paper trading API."""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class OrderSideEnum(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderTypeEnum(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class OrderStatusEnum(str, Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class StrategyDeploymentStatusEnum(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    COMPLETED = "COMPLETED"


# Portfolio schemas
class PaperPortfolioCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    starting_balance: float = Field(default=100000.0, gt=0)


class PaperPositionResponse(BaseModel):
    id: int
    ticker: str
    shares: float
    average_price: float
    market_value: float
    unrealized_pnl: float
    last_price: float
    last_updated: datetime

    class Config:
        from_attributes = True


class PaperPortfolioResponse(BaseModel):
    id: int
    user_id: int
    name: str
    cash_balance: float
    starting_balance: float
    created_at: datetime
    updated_at: datetime
    positions: List[PaperPositionResponse] = []

    class Config:
        from_attributes = True


class PaperPortfolioSummary(BaseModel):
    portfolio_id: int
    portfolio_name: str
    cash_balance: float
    positions_value: float
    total_value: float
    starting_balance: float
    total_pnl: float
    total_pnl_percent: float
    unrealized_pnl: float
    realized_pnl: float
    num_positions: int
    num_closed_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    positions: List[Dict[str, Any]]


# Order schemas
class PaperOrderCreate(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=10)
    side: OrderSideEnum
    quantity: float = Field(..., gt=0)
    order_type: OrderTypeEnum = OrderTypeEnum.MARKET
    limit_price: Optional[float] = Field(None, gt=0)


class PaperOrderResponse(BaseModel):
    id: int
    portfolio_id: int
    ticker: str
    side: OrderSideEnum
    quantity: float
    order_type: OrderTypeEnum
    limit_price: Optional[float]
    status: OrderStatusEnum
    filled_price: Optional[float]
    filled_quantity: float
    created_at: datetime
    filled_at: Optional[datetime]

    class Config:
        from_attributes = True


# Trade schemas
class PaperTradeResponse(BaseModel):
    id: int
    portfolio_id: int
    ticker: str
    entry_price: float
    exit_price: Optional[float]
    shares: float
    pnl: Optional[float]
    pnl_percent: Optional[float]
    opened_at: datetime
    closed_at: Optional[datetime]

    class Config:
        from_attributes = True


# Strategy deployment schemas
class StrategyDeploymentCreate(BaseModel):
    strategy_id: int
    paper_portfolio_id: int


class StrategyDeploymentResponse(BaseModel):
    id: int
    strategy_id: int
    paper_portfolio_id: int
    status: StrategyDeploymentStatusEnum
    deployed_at: datetime
    updated_at: datetime
    last_signal_at: Optional[datetime]

    class Config:
        from_attributes = True


# Execution result schemas
class ExecutionSignal(BaseModel):
    ticker: str
    signal_type: str
    strength: float
    price: Optional[float]
    rules_matched: List[str]


class ExecutionResult(BaseModel):
    action: str
    ticker: str
    shares: float
    price: float
    cost: Optional[float]
    proceeds: Optional[float]
    entry_price: Optional[float]
    pnl: Optional[float]
    pnl_pct: Optional[float]
    order_id: int
    timestamp: datetime


class BatchExecutionResult(BaseModel):
    portfolio_id: int
    executed_signals: List[ExecutionResult]
    skipped_signals: List[ExecutionSignal]
    timestamp: datetime


# Performance metrics schemas
class PerformanceMetrics(BaseModel):
    total_return: float
    total_return_pct: float
    annualized_return: Optional[float]
    sharpe_ratio: Optional[float]
    max_drawdown: Optional[float]
    win_rate: float
    profit_factor: Optional[float]
    num_trades: int
    avg_win: Optional[float]
    avg_loss: Optional[float]


class EquityCurvePoint(BaseModel):
    date: datetime
    equity: float
    daily_return: float


class PortfolioPerformance(BaseModel):
    portfolio_id: int
    metrics: PerformanceMetrics
    equity_curve: List[EquityCurvePoint]
    period_start: datetime
    period_end: datetime
