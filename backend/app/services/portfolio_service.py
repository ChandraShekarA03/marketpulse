from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.portfolio import Portfolio, Holding
from app.schemas.portfolio import PortfolioCreate, HoldingCreate
from app.services.stock_service import get_stock_data
import logging

logger = logging.getLogger(__name__)

def create_portfolio(db: Session, user_id: int, portfolio_in: PortfolioCreate) -> Portfolio:
    db_portfolio = Portfolio(name=portfolio_in.name, user_id=user_id)
    db.add(db_portfolio)
    db.commit()
    db.refresh(db_portfolio)
    return db_portfolio

def get_user_portfolios(db: Session, user_id: int):
    # This just gets the raw db object. Enrichment happens at the API layer or here.
    return db.query(Portfolio).filter(Portfolio.user_id == user_id).all()

def delete_portfolio(db: Session, user_id: int, portfolio_id: int):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.user_id == user_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    db.delete(portfolio)
    db.commit()

def add_holding(db: Session, user_id: int, portfolio_id: int, holding_in: HoldingCreate) -> Holding:
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id, Portfolio.user_id == user_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    # Check if stock exists (validate via stock service)
    try:
        get_stock_data(holding_in.ticker)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid ticker: {holding_in.ticker}")
        
    db_holding = Holding(
        portfolio_id=portfolio_id,
        ticker=holding_in.ticker.upper(),
        shares=holding_in.shares,
        average_buy_price=holding_in.average_buy_price
    )
    db.add(db_holding)
    db.commit()
    db.refresh(db_holding)
    return db_holding

def remove_holding(db: Session, user_id: int, holding_id: int):
    holding = db.query(Holding).join(Portfolio).filter(
        Holding.id == holding_id, 
        Portfolio.user_id == user_id
    ).first()
    
    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")
        
    db.delete(holding)
    db.commit()
    
def enrich_portfolio_with_live_data(portfolio: Portfolio):
    """
    Take a DB portfolio and append live market data to its holdings to calculate
    Total Value, PnL, and Allocation Percentages.
    """
    total_value = 0.0
    total_cost = 0.0
    enriched_holdings = []
    
    for holding in portfolio.holdings:
        try:
            live_data = get_stock_data(holding.ticker)
            current_price = live_data["price"]
        except Exception:
            current_price = holding.average_buy_price # Fallback
            
        current_value = current_price * holding.shares
        cost_basis = holding.average_buy_price * holding.shares
        profit_loss = current_value - cost_basis
        
        total_value += current_value
        total_cost += cost_basis
        
        # We will build a dict that matches the schema
        enriched_holdings.append({
            "id": holding.id,
            "portfolio_id": holding.portfolio_id,
            "ticker": holding.ticker,
            "shares": holding.shares,
            "average_buy_price": holding.average_buy_price,
            "added_at": holding.added_at,
            "current_price": current_price,
            "profit_loss": profit_loss,
            "current_value": current_value
        })
        
    # Calculate allocations
    for eh in enriched_holdings:
        if total_value > 0:
            eh["allocation_percentage"] = (eh["current_value"] / total_value) * 100
        else:
            eh["allocation_percentage"] = 0.0
            
    total_profit_loss = total_value - total_cost
    
    # Simple risk score heuristic based on number of holdings (more holdings = lower risk)
    risk_score = max(10, 100 - (len(enriched_holdings) * 10)) if enriched_holdings else 0
    
    return {
        "id": portfolio.id,
        "name": portfolio.name,
        "user_id": portfolio.user_id,
        "created_at": portfolio.created_at,
        "holdings": enriched_holdings,
        "total_value": total_value,
        "total_profit_loss": total_profit_loss,
        "risk_score": float(risk_score)
    }


def get_portfolio_overview(db: Session, user_id: int):
    portfolios = get_user_portfolios(db, user_id)
    enriched = [enrich_portfolio_with_live_data(portfolio) for portfolio in portfolios]
    total_value = sum(portfolio["total_value"] for portfolio in enriched)
    total_profit_loss = sum(portfolio["total_profit_loss"] for portfolio in enriched)
    all_holdings = [holding for portfolio in enriched for holding in portfolio["holdings"]]
    symbols = list({holding["ticker"] for holding in all_holdings})

    return {
        "portfolio_count": len(enriched),
        "total_value": total_value,
        "total_profit_loss": total_profit_loss,
        "portfolio_risk_score": float(sum(portfolio["risk_score"] for portfolio in enriched) / len(enriched)) if enriched else 0.0,
        "holdings": all_holdings,
        "symbols": symbols,
        "portfolios": enriched,
    }
