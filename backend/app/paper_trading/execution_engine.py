"""Main execution engine for paper trading."""
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.paper_trading import OrderSide, OrderType, StrategyDeploymentStatus
from app.paper_trading.order_manager import OrderManager
from app.paper_trading.portfolio_engine import PortfolioEngine
from app.paper_trading.signal_processor import Signal
import logging

logger = logging.getLogger(__name__)


class ExecutionEngine:
    """Main execution engine for paper trading strategies."""

    # Risk management parameters
    MAX_POSITION_SIZE = 0.25  # 25% of portfolio per position
    MAX_ORDER_SIZE = 0.10  # 10% of portfolio per order
    MIN_CASH_RESERVE = 0.05  # Keep 5% cash minimum

    @staticmethod
    def execute_signal(
        db: Session,
        portfolio_id: int,
        signal: Signal,
        position_size_pct: float = 0.05,
    ) -> Optional[Dict[str, Any]]:
        """Execute a trading signal."""
        portfolio = PortfolioEngine.get_portfolio(db, portfolio_id)
        if not portfolio:
            logger.error(f"Portfolio {portfolio_id} not found")
            return None

        # Get current price
        if signal.price is None:
            logger.warning(f"No price available for signal {signal.ticker}")
            return None

        try:
            if signal.signal_type == "BUY":
                return ExecutionEngine._execute_buy(
                    db=db,
                    portfolio=portfolio,
                    ticker=signal.ticker,
                    current_price=signal.price,
                    position_size_pct=position_size_pct,
                )
            elif signal.signal_type == "SELL":
                return ExecutionEngine._execute_sell(
                    db=db,
                    portfolio=portfolio,
                    ticker=signal.ticker,
                    current_price=signal.price,
                )
        except Exception as e:
            logger.error(f"Error executing signal for {signal.ticker}: {e}")
            return None

    @staticmethod
    def _execute_buy(
        db: Session,
        portfolio: Any,
        ticker: str,
        current_price: float,
        position_size_pct: float = 0.05,
    ) -> Optional[Dict[str, Any]]:
        """Execute a buy order."""
        # Get portfolio value
        portfolio_summary = PortfolioEngine.get_portfolio_summary(db, portfolio.id)
        portfolio_value = portfolio_summary["total_value"]

        # Calculate position size
        target_position_value = portfolio_value * position_size_pct
        max_position_value = portfolio_value * ExecutionEngine.MAX_POSITION_SIZE
        min_cash = portfolio_value * ExecutionEngine.MIN_CASH_RESERVE

        # Check if we would violate max position size
        if target_position_value > max_position_value:
            target_position_value = max_position_value

        # Calculate shares to buy
        shares = int(target_position_value / current_price)
        cost = shares * current_price

        # Check cash availability
        if portfolio.cash_balance - cost < min_cash:
            logger.warning(
                f"Insufficient cash for buy order: need {cost}, "
                f"have {portfolio.cash_balance}, min required {min_cash}"
            )
            return None

        if shares <= 0:
            logger.warning(f"Order size too small for {ticker} at ${current_price}")
            return None

        try:
            # Execute market order
            result = OrderManager.execute_market_order(
                db=db,
                portfolio_id=portfolio.id,
                ticker=ticker,
                side=OrderSide.BUY,
                quantity=shares,
            )

            # Update portfolio
            PortfolioEngine.add_position(
                db=db,
                portfolio_id=portfolio.id,
                ticker=ticker,
                shares=shares,
                price=current_price,
            )

            # Update cash
            PortfolioEngine.update_cash_balance(
                db=db,
                portfolio_id=portfolio.id,
                amount=-cost,
                description=f"BUY {shares} {ticker}",
            )

            logger.info(f"Bought {shares} shares of {ticker} at ${current_price}")
            return {
                "action": "BUY",
                "ticker": ticker,
                "shares": shares,
                "price": current_price,
                "cost": cost,
                "order_id": result["order_id"],
                "timestamp": datetime.utcnow(),
            }

        except Exception as e:
            logger.error(f"Error executing buy order for {ticker}: {e}")
            return None

    @staticmethod
    def _execute_sell(
        db: Session,
        portfolio: Any,
        ticker: str,
        current_price: float,
    ) -> Optional[Dict[str, Any]]:
        """Execute a sell order (close position)."""
        # Find existing position
        position = next(
            (p for p in portfolio.positions if p.ticker == ticker.upper()),
            None,
        )

        if not position or position.shares <= 0:
            logger.warning(f"No position to sell for {ticker}")
            return None

        shares = position.shares
        proceeds = shares * current_price

        try:
            # Record trade
            entry_price = position.average_price
            PortfolioEngine.record_trade(
                db=db,
                portfolio_id=portfolio.id,
                ticker=ticker,
                entry_price=entry_price,
                exit_price=current_price,
                shares=shares,
            )

            # Execute market order
            result = OrderManager.execute_market_order(
                db=db,
                portfolio_id=portfolio.id,
                ticker=ticker,
                side=OrderSide.SELL,
                quantity=shares,
            )

            # Update position
            PortfolioEngine.reduce_position(
                db=db,
                portfolio_id=portfolio.id,
                ticker=ticker,
                shares=shares,
            )

            # Update cash
            PortfolioEngine.update_cash_balance(
                db=db,
                portfolio_id=portfolio.id,
                amount=proceeds,
                description=f"SELL {shares} {ticker}",
            )

            pnl = (current_price - entry_price) * shares
            pnl_pct = (pnl / (entry_price * shares) * 100) if entry_price > 0 else 0

            logger.info(f"Sold {shares} shares of {ticker} at ${current_price}, PnL: ${pnl}")
            return {
                "action": "SELL",
                "ticker": ticker,
                "shares": shares,
                "price": current_price,
                "proceeds": proceeds,
                "entry_price": entry_price,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "order_id": result["order_id"],
                "timestamp": datetime.utcnow(),
            }

        except Exception as e:
            logger.error(f"Error executing sell order for {ticker}: {e}")
            return None

    @staticmethod
    def execute_signals_batch(
        db: Session,
        portfolio_id: int,
        signals: List[Signal],
        position_size_pct: float = 0.05,
    ) -> Dict[str, Any]:
        """Execute multiple signals in sequence."""
        results = {
            "portfolio_id": portfolio_id,
            "executed_signals": [],
            "skipped_signals": [],
            "timestamp": datetime.utcnow(),
        }

        for signal in signals:
            result = ExecutionEngine.execute_signal(
                db=db,
                portfolio_id=portfolio_id,
                signal=signal,
                position_size_pct=position_size_pct,
            )

            if result:
                results["executed_signals"].append(result)
            else:
                results["skipped_signals"].append(signal.to_dict())

        return results
