"""Signal processing and strategy evaluation for paper trading."""
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from app.backtesting.strategy_parser import parse_signals
from app.backtesting.indicators import compute_indicators
from app.services.stock_service import get_historical_data
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class Signal:
    """Represents a trading signal."""
    
    def __init__(
        self,
        ticker: str,
        signal_type: str,  # "BUY" or "SELL"
        strength: float = 1.0,  # 0.0 to 1.0
        price: Optional[float] = None,
        rules_matched: Optional[List[str]] = None,
    ):
        self.ticker = ticker
        self.signal_type = signal_type
        self.strength = strength
        self.price = price
        self.rules_matched = rules_matched or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "signal_type": self.signal_type,
            "strength": self.strength,
            "price": self.price,
            "rules_matched": self.rules_matched,
        }


class SignalProcessor:
    """Processes market data and generates trading signals from strategies."""

    @staticmethod
    def evaluate_strategy(
        ticker: str,
        rules: Dict[str, Any],
        lookback_days: int = 30,
    ) -> Optional[Signal]:
        """Evaluate strategy rules for a given ticker and generate signals."""
        try:
            # Fetch historical data
            raw_data = get_historical_data(ticker, outputsize="full")
            if not raw_data or len(raw_data) < lookback_days:
                logger.warning(f"Insufficient historical data for {ticker}")
                return None

            # Convert to DataFrame
            df = pd.DataFrame(raw_data)
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").set_index("date")
            
            # Use only recent data
            df = df.tail(lookback_days).copy()

            # Compute indicators
            df = compute_indicators(df)

            # Parse and evaluate signals
            entries, exits = parse_signals(df, rules)

            # Get latest signal (most recent bar)
            if len(entries) > 0 and entries.iloc[-1]:
                return Signal(
                    ticker=ticker,
                    signal_type="BUY",
                    strength=1.0,
                    price=df["close"].iloc[-1] if "close" in df.columns else None,
                    rules_matched=["entry_condition"],
                )
            elif len(exits) > 0 and exits.iloc[-1]:
                return Signal(
                    ticker=ticker,
                    signal_type="SELL",
                    strength=1.0,
                    price=df["close"].iloc[-1] if "close" in df.columns else None,
                    rules_matched=["exit_condition"],
                )

            return None

        except Exception as e:
            logger.error(f"Error evaluating strategy for {ticker}: {e}")
            return None

    @staticmethod
    def evaluate_multiple_strategies(
        db: Session,
        portfolio_deployments: List[Any],
        lookback_days: int = 30,
    ) -> List[Signal]:
        """Evaluate all active strategies and collect signals."""
        signals = []

        for deployment in portfolio_deployments:
            strategy = deployment.strategy
            if not strategy or strategy.rules_json is None:
                continue

            try:
                # Get the tickers from the strategy (if stored)
                tickers = strategy.tickers if hasattr(strategy, "tickers") else []
                if not tickers:
                    logger.warning(f"Strategy {strategy.id} has no tickers")
                    continue

                for ticker in tickers:
                    signal = SignalProcessor.evaluate_strategy(
                        ticker=ticker,
                        rules=strategy.rules_json,
                        lookback_days=lookback_days,
                    )
                    if signal:
                        signals.append(signal)

            except Exception as e:
                logger.error(f"Error evaluating deployment {deployment.id}: {e}")

        return signals

    @staticmethod
    def filter_signals(
        signals: List[Signal],
        min_strength: float = 0.5,
        signal_type: Optional[str] = None,
    ) -> List[Signal]:
        """Filter signals based on criteria."""
        filtered = [
            s for s in signals
            if s.strength >= min_strength
            and (signal_type is None or s.signal_type == signal_type)
        ]
        return filtered

    @staticmethod
    def rank_signals(signals: List[Signal]) -> List[Signal]:
        """Rank signals by strength (descending)."""
        return sorted(signals, key=lambda s: s.strength, reverse=True)
