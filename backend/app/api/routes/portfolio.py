from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.user import User
from app.schemas.portfolio import PortfolioCreate, PortfolioResponse, HoldingCreate, HoldingResponse
from app.api.dependencies import get_current_active_user
from app.services import portfolio_service

router = APIRouter(
    prefix="/portfolio",
    tags=["Portfolio"]
)

@router.post("", response_model=PortfolioResponse)
def create_portfolio(
    portfolio_in: PortfolioCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new portfolio for the authenticated user."""
    db_port = portfolio_service.create_portfolio(db, current_user.id, portfolio_in)
    return portfolio_service.enrich_portfolio_with_live_data(db_port)

@router.get("", response_model=List[PortfolioResponse])
def get_portfolios(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all portfolios for the user, enriched with live market data."""
    portfolios = portfolio_service.get_user_portfolios(db, current_user.id)
    return [portfolio_service.enrich_portfolio_with_live_data(p) for p in portfolios]

@router.delete("/{portfolio_id}")
def delete_portfolio(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a portfolio."""
    portfolio_service.delete_portfolio(db, current_user.id, portfolio_id)
    return {"message": "Portfolio deleted successfully"}

@router.post("/{portfolio_id}/holdings", response_model=HoldingResponse)
def add_holding(
    portfolio_id: int,
    holding_in: HoldingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Add a new stock holding to a portfolio."""
    return portfolio_service.add_holding(db, current_user.id, portfolio_id, holding_in)

@router.delete("/holdings/{holding_id}")
def remove_holding(
    holding_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Remove a holding from a portfolio."""
    portfolio_service.remove_holding(db, current_user.id, holding_id)
    return {"message": "Holding removed successfully"}
