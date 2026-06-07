"""Portfolio management for paper trading."""
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.paper_trading import PaperPortfolio, PaperPosition, PaperTrade, OrderSide
from app.services.stock_service import get_stock_data
import logging

logger = logging.getLogger(__name__)


class PortfolioEngine:
    """Manages positions, cash, and PnL calculations."""

    @staticmethod
    def create_portfolio(
        db: Session,
        user_id: int,
        name: str,
        starting_balance: float = 100000.0,
    ) -> PaperPortfolio:
        """Create a new paper portfolio."""
        if starting_balance <= 0:
            raise ValueError("Starting balance must be positive")

        portfolio = PaperPortfolio(
            user_id=user_id,
            name=name,
            cash_balance=starting_balance,
            starting_balance=starting_balance,
        )
        db.add(portfolio)
        db.commit()
        db.refresh(portfolio)
        return portfolio

    @staticmethod
    def get_portfolio(db: Session, portfolio_id: int) -> PaperPortfolio:
        """Get a portfolio by ID."""
        return db.query(PaperPortfolio).filter(PaperPortfolio.id == portfolio_id).first()

    @staticmethod
    def add_position(
        db: Session,
        portfolio_id: int,
        ticker: str,
        shares: float,
        price: float,
    ) -> PaperPosition:
        """Add or update a position."""
        if shares <= 0 or price <= 0:
            raise ValueError("Shares and price must be positive")

        ticker = ticker.upper()
        position = db.query(PaperPosition).filter(
            PaperPosition.portfolio_id == portfolio_id,
            PaperPosition.ticker == ticker,
        ).first()

        if position:
            # Update existing position (average down/up)
            total_cost = position.average_price * position.shares + price * shares
            position.shares += shares
            position.average_price = total_cost / position.shares if position.shares > 0 else 0
        else:
            # Create new position
            position = PaperPosition(
                portfolio_id=portfolio_id,
                ticker=ticker,
                shares=shares,
                average_price=price,
            )
            db.add(position)

        position.market_value = position.shares * price
        db.commit()
        db.refresh(position)
        return position

    @staticmethod
    def reduce_position(
        db: Session,
        portfolio_id: int,
        ticker: str,
        shares: float,
    ) -> Optional[PaperPosition]:
        """Reduce a position (sell shares)."""
        if shares <= 0:
            raise ValueError("Shares must be positive")

        ticker = ticker.upper()
        position = db.query(PaperPosition).filter(
            PaperPosition.portfolio_id == portfolio_id,
            PaperPosition.ticker == ticker,
        ).first()

        if not position or position.shares < shares:
            raise ValueError(f"Insufficient shares of {ticker}")

        position.shares -= shares
        
        if position.shares == 0:
            db.delete(position)
        else:
            position.market_value = position.shares * position.last_price
        
        db.commit()
        return position

    @staticmethod
    def update_position_prices(db: Session, portfolio_id: int) -> Dict[str, Any]:
        """Fetch current prices and update all positions."""
        portfolio = PortfolioEngine.get_portfolio(db, portfolio_id)
        if not portfolio:
            raise ValueError(f"Portfolio {portfolio_id} not found")

        positions = portfolio.positions
        total_position_value = 0.0
        updated_count = 0

        for position in positions:
            try:
                stock_data = get_stock_data(position.ticker)
                current_price = stock_data["price"]
                
                position.last_price = current_price
                position.market_value = position.shares * current_price
                position.unrealized_pnl = (current_price - position.average_price) * position.shares
                position.last_updated = datetime.utcnow()
                total_position_value += position.market_value
                updated_count += 1
            except Exception as e:
                logger.warning(f"Failed to update price for {position.ticker}: {e}")
                total_position_value += position.market_value

        db.commit()

        total_value = portfolio.cash_balance + total_position_value
        total_pnl = total_value - portfolio.starting_balance
        total_pnl_percent = (total_pnl / portfolio.starting_balance * 100) if portfolio.starting_balance > 0 else 0

        return {
            "portfolio_id": portfolio_id,
            "cash_balance": portfolio.cash_balance,
            "positions_value": total_position_value,
            "total_value": total_value,
            "total_pnl": total_pnl,
            "total_pnl_percent": total_pnl_percent,
            "positions_updated": updated_count,
            "timestamp": datetime.utcnow(),
        }

    @staticmethod
    def update_cash_balance(
        db: Session,
        portfolio_id: int,
        amount: float,
        description: str = "",
    ) -> PaperPortfolio:
        """Update cash balance (used for buy/sell orders)."""
        portfolio = PortfolioEngine.get_portfolio(db, portfolio_id)
        if not portfolio:
            raise ValueError(f"Portfolio {portfolio_id} not found")

        portfolio.cash_balance += amount
        if portfolio.cash_balance < 0:
            raise ValueError("Insufficient cash balance")

        db.commit()
        db.refresh(portfolio)
        logger.info(f"Portfolio {portfolio_id}: cash updated by {amount} ({description})")
        return portfolio

    @staticmethod
    def record_trade(
        db: Session,
        portfolio_id: int,
        ticker: str,
        entry_price: float,
        exit_price: Optional[float] = None,
        shares: float = 0,
    ) -> PaperTrade:
        """Record a closed trade."""
        trade = PaperTrade(
            portfolio_id=portfolio_id,
            ticker=ticker.upper(),
            entry_price=entry_price,
            exit_price=exit_price,
            shares=shares,
        )

        if exit_price is not None and shares > 0:
            trade.pnl = (exit_price - entry_price) * shares
            trade.pnl_percent = ((exit_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
            trade.closed_at = datetime.utcnow()

        db.add(trade)
        db.commit()
        db.refresh(trade)
        return trade

    @staticmethod
    def get_portfolio_summary(db: Session, portfolio_id: int) -> Dict[str, Any]:
        """Get complete portfolio summary."""
        portfolio = PortfolioEngine.get_portfolio(db, portfolio_id)
        if not portfolio:
            raise ValueError(f"Portfolio {portfolio_id} not found")

        positions = portfolio.positions
        total_position_value = sum(p.market_value for p in positions)
        total_unrealized_pnl = sum(p.unrealized_pnl for p in positions)

        # Calculate closed trades stats
        trades = portfolio.trades
        total_realized_pnl = sum(t.pnl for t in trades if t.pnl is not None)
        winning_trades = len([t for t in trades if t.pnl and t.pnl > 0])
        losing_trades = len([t for t in trades if t.pnl and t.pnl < 0])

        total_value = portfolio.cash_balance + total_position_value
        total_pnl = total_unrealized_pnl + total_realized_pnl
        total_pnl_percent = (total_pnl / portfolio.starting_balance * 100) if portfolio.starting_balance > 0 else 0

        return {
            "portfolio_id": portfolio_id,
            "portfolio_name": portfolio.name,
            "cash_balance": portfolio.cash_balance,
            "positions_value": total_position_value,
            "total_value": total_value,
            "starting_balance": portfolio.starting_balance,
            "total_pnl": total_pnl,
            "total_pnl_percent": total_pnl_percent,
            "unrealized_pnl": total_unrealized_pnl,
            "realized_pnl": total_realized_pnl,
            "num_positions": len(positions),
            "num_closed_trades": len(trades),
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": (winning_trades / len(trades) * 100) if trades else 0,
            "positions": [
                {
                    "ticker": p.ticker,
                    "shares": p.shares,
                    "average_price": p.average_price,
                    "last_price": p.last_price,
                    "market_value": p.market_value,
                    "unrealized_pnl": p.unrealized_pnl,
                }
                for p in positions
            ],
        }
