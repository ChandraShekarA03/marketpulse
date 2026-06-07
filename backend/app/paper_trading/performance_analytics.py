"""Performance analytics for paper trading portfolios."""
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from app.models.paper_trading import PaperPortfolio, PaperTrade
import logging

logger = logging.getLogger(__name__)


class PerformanceAnalytics:
    """Calculate performance metrics and equity curves for paper portfolios."""

    # Constants
    RISK_FREE_RATE = 0.02  # 2% annual risk-free rate
    TRADING_DAYS_PER_YEAR = 252

    @staticmethod
    def calculate_performance(db: Session, portfolio_id: int) -> Dict[str, Any]:
        """Calculate comprehensive performance metrics for a portfolio."""
        portfolio = db.query(PaperPortfolio).filter(PaperPortfolio.id == portfolio_id).first()
        if not portfolio:
            raise ValueError(f"Portfolio {portfolio_id} not found")

        # Get equity curve
        equity_curve = PerformanceAnalytics.build_equity_curve(db, portfolio_id)
        if not equity_curve:
            raise ValueError(f"No equity history for portfolio {portfolio_id}")

        # Calculate metrics
        metrics = PerformanceAnalytics.calculate_metrics(portfolio, equity_curve)

        return {
            "portfolio_id": portfolio_id,
            "metrics": metrics,
            "equity_curve": equity_curve,
            "period_start": portfolio.created_at,
            "period_end": datetime.utcnow(),
        }

    @staticmethod
    def build_equity_curve(db: Session, portfolio_id: int) -> List[Dict[str, Any]]:
        """Build equity curve from portfolio history."""
        portfolio = db.query(PaperPortfolio).filter(PaperPortfolio.id == portfolio_id).first()
        if not portfolio:
            return []

        from app.paper_trading.portfolio_engine import PortfolioEngine
        summary = PortfolioEngine.get_portfolio_summary(db, portfolio_id)

        # Start with initial value
        equity_points = [
            {
                "date": portfolio.created_at,
                "equity": portfolio.starting_balance,
                "daily_return": 0.0,
            }
        ]

        # Add current value
        current_time = datetime.utcnow()
        if (current_time - portfolio.created_at).total_seconds() > 60:  # If more than 1 minute
            daily_return = (
                (summary["total_value"] - portfolio.starting_balance) / portfolio.starting_balance
                if portfolio.starting_balance > 0
                else 0.0
            )
            equity_points.append(
                {
                    "date": current_time,
                    "equity": summary["total_value"],
                    "daily_return": daily_return,
                }
            )

        return equity_points

    @staticmethod
    def calculate_metrics(portfolio: PaperPortfolio, equity_curve: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate performance metrics."""
        if not equity_curve or len(equity_curve) < 2:
            return {
                "total_return": 0.0,
                "total_return_pct": 0.0,
                "annualized_return": None,
                "sharpe_ratio": None,
                "max_drawdown": None,
                "win_rate": 0.0,
                "profit_factor": None,
                "num_trades": 0,
                "avg_win": None,
                "avg_loss": None,
            }

        # Calculate returns
        starting_value = portfolio.starting_balance
        ending_value = equity_curve[-1]["equity"]
        total_return = ending_value - starting_value
        total_return_pct = (total_return / starting_value * 100) if starting_value > 0 else 0.0

        # Calculate annualized return
        days_elapsed = (equity_curve[-1]["date"] - equity_curve[0]["date"]).days
        years_elapsed = days_elapsed / 365.0 if days_elapsed > 0 else 0
        annualized_return = None
        if years_elapsed > 0 and starting_value > 0:
            annualized_return = ((ending_value / starting_value) ** (1 / years_elapsed) - 1) * 100

        # Calculate Sharpe ratio
        sharpe_ratio = PerformanceAnalytics.calculate_sharpe_ratio(
            equity_curve, years_elapsed
        )

        # Calculate max drawdown
        max_drawdown = PerformanceAnalytics.calculate_max_drawdown(equity_curve)

        # Get trade statistics
        win_rate, profit_factor, num_trades, avg_win, avg_loss = PerformanceAnalytics.calculate_trade_stats(portfolio)

        return {
            "total_return": total_return,
            "total_return_pct": total_return_pct,
            "annualized_return": annualized_return,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "num_trades": num_trades,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
        }

    @staticmethod
    def calculate_sharpe_ratio(equity_curve: List[Dict[str, Any]], years_elapsed: float) -> Optional[float]:
        """Calculate Sharpe ratio."""
        if len(equity_curve) < 2 or years_elapsed <= 0:
            return None

        try:
            # Convert equity curve to returns
            equities = np.array([point["equity"] for point in equity_curve])
            returns = np.diff(equities) / equities[:-1]

            # Calculate excess return and volatility
            excess_returns = returns - (PerformanceAnalytics.RISK_FREE_RATE / PerformanceAnalytics.TRADING_DAYS_PER_YEAR)
            volatility = np.std(excess_returns)

            if volatility == 0:
                return 0.0

            # Annualized Sharpe ratio
            sharpe = (np.mean(excess_returns) * PerformanceAnalytics.TRADING_DAYS_PER_YEAR) / volatility
            return float(sharpe)

        except Exception as e:
            logger.warning(f"Error calculating Sharpe ratio: {e}")
            return None

    @staticmethod
    def calculate_max_drawdown(equity_curve: List[Dict[str, Any]]) -> Optional[float]:
        """Calculate maximum drawdown."""
        if len(equity_curve) < 2:
            return None

        try:
            equities = np.array([point["equity"] for point in equity_curve])
            cumulative_max = np.maximum.accumulate(equities)
            drawdown = (equities - cumulative_max) / cumulative_max
            max_drawdown = np.min(drawdown) * 100

            return float(max_drawdown)

        except Exception as e:
            logger.warning(f"Error calculating max drawdown: {e}")
            return None

    @staticmethod
    def calculate_trade_stats(portfolio: PaperPortfolio) -> Tuple[float, Optional[float], int, Optional[float], Optional[float]]:
        """Calculate trade statistics."""
        from app.models.paper_trading import PaperTrade
        from app.core.database import SessionLocal

        try:
            db = SessionLocal()
            trades = db.query(PaperTrade).filter(
                PaperTrade.portfolio_id == portfolio.id,
                PaperTrade.closed_at.isnot(None),
                PaperTrade.pnl.isnot(None),
            ).all()
            db.close()

            if not trades:
                return 0.0, None, 0, None, None

            num_trades = len(trades)
            pnls = [t.pnl for t in trades if t.pnl is not None]
            winning_trades = [p for p in pnls if p > 0]
            losing_trades = [p for p in pnls if p < 0]

            win_rate = (len(winning_trades) / len(pnls) * 100) if pnls else 0.0

            total_wins = sum(winning_trades)
            total_losses = sum([abs(l) for l in losing_trades])
            profit_factor = (total_wins / total_losses) if total_losses > 0 else None

            avg_win = (sum(winning_trades) / len(winning_trades)) if winning_trades else None
            avg_loss = (sum(losing_trades) / len(losing_trades)) if losing_trades else None

            return win_rate, profit_factor, num_trades, avg_win, avg_loss

        except Exception as e:
            logger.error(f"Error calculating trade stats: {e}")
            return 0.0, None, 0, None, None

    @staticmethod
    def get_returns_series(
        db: Session,
        portfolio_id: int,
        period: str = "daily",
    ) -> pd.DataFrame:
        """Get returns time series for portfolio."""
        from app.paper_trading.portfolio_engine import PortfolioEngine

        portfolio = PortfolioEngine.get_portfolio(db, portfolio_id)
        if not portfolio:
            return pd.DataFrame()

        equity_curve = PerformanceAnalytics.build_equity_curve(db, portfolio_id)
        if not equity_curve:
            return pd.DataFrame()

        df = pd.DataFrame(equity_curve)
        df["date"] = pd.to_datetime(df["date"])
        df["return"] = df["equity"].pct_change() * 100

        if period == "daily":
            return df
        elif period == "weekly":
            df.set_index("date", inplace=True)
            return df.resample("W").agg({"equity": "last", "return": "sum"}).reset_index()
        elif period == "monthly":
            df.set_index("date", inplace=True)
            return df.resample("M").agg({"equity": "last", "return": "sum"}).reset_index()
        else:
            return df

    @staticmethod
    def compare_portfolios(
        db: Session,
        portfolio_ids: List[int],
    ) -> Dict[str, Any]:
        """Compare performance across multiple portfolios."""
        comparison = {}

        for portfolio_id in portfolio_ids:
            try:
                portfolio = db.query(PaperPortfolio).filter(
                    PaperPortfolio.id == portfolio_id
                ).first()
                if portfolio:
                    summary = PerformanceAnalytics.calculate_performance(db, portfolio_id)
                    comparison[f"portfolio_{portfolio_id}"] = {
                        "name": portfolio.name,
                        "metrics": summary["metrics"],
                    }
            except Exception as e:
                logger.error(f"Error comparing portfolio {portfolio_id}: {e}")

        return comparison
