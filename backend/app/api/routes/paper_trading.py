"""Paper trading API routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.paper_trading import (
    PaperPortfolio, PaperOrder, PaperTrade, StrategyDeployment,
    StrategyDeploymentStatus, OrderSide, OrderStatus
)
from app.schemas.paper_trading import (
    PaperPortfolioCreate, PaperPortfolioResponse, PaperPortfolioSummary,
    PaperOrderCreate, PaperOrderResponse, PaperTradeResponse,
    StrategyDeploymentCreate, StrategyDeploymentResponse,
    ExecutionResult, BatchExecutionResult, PortfolioPerformance,
)
from app.paper_trading.portfolio_engine import PortfolioEngine
from app.paper_trading.order_manager import OrderManager
from app.paper_trading.signal_processor import Signal

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/paper", tags=["paper_trading"])


# Portfolio endpoints
@router.post("/portfolio", response_model=PaperPortfolioResponse)
async def create_portfolio(
    portfolio_data: PaperPortfolioCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new paper trading portfolio."""
    portfolio = PortfolioEngine.create_portfolio(
        db=db,
        user_id=current_user.id,
        name=portfolio_data.name,
        starting_balance=portfolio_data.starting_balance,
    )
    return portfolio


@router.get("/portfolio/{portfolio_id}", response_model=PaperPortfolioResponse)
async def get_portfolio(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a paper portfolio."""
    portfolio = PortfolioEngine.get_portfolio(db, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if portfolio.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    return portfolio


@router.get("/portfolio/{portfolio_id}/summary", response_model=PaperPortfolioSummary)
async def get_portfolio_summary(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get portfolio summary with performance metrics."""
    portfolio = PortfolioEngine.get_portfolio(db, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if portfolio.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    summary = PortfolioEngine.get_portfolio_summary(db, portfolio_id)
    return summary


@router.get("/portfolios", response_model=List[PaperPortfolioResponse])
async def list_portfolios(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all paper portfolios for current user."""
    portfolios = db.query(PaperPortfolio).filter(
        PaperPortfolio.user_id == current_user.id
    ).all()
    return portfolios


@router.post("/portfolio/{portfolio_id}/update-prices")
async def update_portfolio_prices(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually trigger price update for a portfolio."""
    portfolio = PortfolioEngine.get_portfolio(db, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if portfolio.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    result = PortfolioEngine.update_position_prices(db, portfolio_id)
    return result


# Order endpoints
@router.post("/order", response_model=PaperOrderResponse)
async def place_order(
    order_data: PaperOrderCreate,
    portfolio_id: int = Query(..., gt=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Place a new order."""
    portfolio = PortfolioEngine.get_portfolio(db, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if portfolio.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    try:
        order = OrderManager.create_order(
            db=db,
            portfolio_id=portfolio_id,
            ticker=order_data.ticker,
            side=order_data.side,
            quantity=order_data.quantity,
            order_type=order_data.order_type,
            limit_price=order_data.limit_price,
        )
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/orders", response_model=List[PaperOrderResponse])
async def list_orders(
    portfolio_id: int = Query(..., gt=0),
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List orders for a portfolio."""
    portfolio = PortfolioEngine.get_portfolio(db, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if portfolio.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    query = db.query(PaperOrder).filter(PaperOrder.portfolio_id == portfolio_id)
    if status:
        try:
            status_enum = OrderStatus[status]
            query = query.filter(PaperOrder.status == status_enum)
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    return query.all()


@router.post("/order/{order_id}/cancel", response_model=PaperOrderResponse)
async def cancel_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel a pending order."""
    order = db.query(PaperOrder).filter(PaperOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    portfolio = PortfolioEngine.get_portfolio(db, order.portfolio_id)
    if portfolio.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    try:
        order = OrderManager.cancel_order(db, order)
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Trade endpoints
@router.get("/trades", response_model=List[PaperTradeResponse])
async def list_trades(
    portfolio_id: int = Query(..., gt=0),
    ticker: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List closed trades for a portfolio."""
    portfolio = PortfolioEngine.get_portfolio(db, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if portfolio.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    query = db.query(PaperTrade).filter(PaperTrade.portfolio_id == portfolio_id)
    if ticker:
        query = query.filter(PaperTrade.ticker == ticker.upper())

    return query.order_by(PaperTrade.opened_at.desc()).all()


# Strategy deployment endpoints
@router.post("/deploy-strategy", response_model=StrategyDeploymentResponse)
async def deploy_strategy(
    deployment_data: StrategyDeploymentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deploy a strategy to a paper portfolio."""
    portfolio = PortfolioEngine.get_portfolio(db, deployment_data.paper_portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if portfolio.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Check if strategy exists and belongs to user
    from app.models.strategy import Strategy
    strategy = db.query(Strategy).filter(
        Strategy.id == deployment_data.strategy_id,
        Strategy.user_id == current_user.id,
    ).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    # Check if already deployed
    existing = db.query(StrategyDeployment).filter(
        StrategyDeployment.strategy_id == deployment_data.strategy_id,
        StrategyDeployment.paper_portfolio_id == deployment_data.paper_portfolio_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Strategy already deployed to this portfolio")

    deployment = StrategyDeployment(
        strategy_id=deployment_data.strategy_id,
        paper_portfolio_id=deployment_data.paper_portfolio_id,
        status=StrategyDeploymentStatus.ACTIVE,
    )
    db.add(deployment)
    db.commit()
    db.refresh(deployment)
    return deployment


@router.get("/deployments", response_model=List[StrategyDeploymentResponse])
async def list_deployments(
    portfolio_id: int = Query(..., gt=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List strategy deployments for a portfolio."""
    portfolio = PortfolioEngine.get_portfolio(db, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if portfolio.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    deployments = db.query(StrategyDeployment).filter(
        StrategyDeployment.paper_portfolio_id == portfolio_id
    ).all()
    return deployments


@router.post("/deployment/{deployment_id}/status/{new_status}")
async def update_deployment_status(
    deployment_id: int,
    new_status: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update strategy deployment status."""
    deployment = db.query(StrategyDeployment).filter(
        StrategyDeployment.id == deployment_id
    ).first()
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    portfolio = PortfolioEngine.get_portfolio(db, deployment.paper_portfolio_id)
    if portfolio.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    try:
        deployment.status = StrategyDeploymentStatus[new_status]
        db.commit()
        db.refresh(deployment)
        return deployment
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {new_status}")


# Performance endpoints
@router.get("/performance/{portfolio_id}", response_model=PortfolioPerformance)
async def get_performance(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get portfolio performance metrics and equity curve."""
    portfolio = PortfolioEngine.get_portfolio(db, portfolio_id)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if portfolio.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    from app.paper_trading.performance_analytics import PerformanceAnalytics
    performance = PerformanceAnalytics.calculate_performance(db, portfolio_id)
    return performance
