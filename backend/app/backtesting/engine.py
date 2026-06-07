import pandas as pd
from typing import Any, Dict

from app.backtesting.indicators import compute_indicators
from app.backtesting.strategy_parser import parse_signals
from app.backtesting.metrics import compute_metrics
from app.services.stock_service import get_historical_data


class BacktestEngine:
    def run(self, rules_json: Dict[str, Any], ticker: str, start_date: str, end_date: str) -> Dict[str, Any]:
        raw_data = get_historical_data(ticker, outputsize="full")
        df = pd.DataFrame(raw_data)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").set_index("date")
        df = df.loc[start_date:end_date].copy()

        if df.empty:
            raise ValueError("No historical data available for the requested date range.")
        if len(df) < 20:
            raise ValueError("Not enough historical data to run a robust backtest.")

        df = compute_indicators(df)
        entries, exits = parse_signals(df, rules_json)

        entries = entries.astype(bool)
        exits = exits.astype(bool)

        import vectorbt as vbt

        portfolio = vbt.Portfolio.from_signals(
            close=df["close"],
            entries=entries,
            exits=exits,
            init_cash=10000,
            fees=0.0005,
            slippage=0.0,
            freq="1D",
        )

        metrics = compute_metrics(portfolio)
        equity_curve = [
            {"date": idx.strftime("%Y-%m-%d"), "equity": float(value)}
            for idx, value in portfolio.value().items()
        ]

        trade_records = pd.DataFrame(portfolio.trades.records_readable)
        trades = []
        if not trade_records.empty:
            for row in trade_records.to_dict("records"):
                trades.append(
                    {
                        "entry_date": str(row.get("EntryDate")) if row.get("EntryDate") is not None else None,
                        "exit_date": str(row.get("ExitDate")) if row.get("ExitDate") is not None else None,
                        "size": float(row.get("Size") or 0.0),
                        "entry_price": float(row.get("EntryPrice") or 0.0),
                        "exit_price": float(row.get("ExitPrice") or 0.0),
                        "return_pct": float(row.get("ReturnPct") or 0.0),
                        "pnl": float(row.get("PnL") or 0.0),
                    }
                )

        return {
            "ticker": ticker.upper(),
            "start_date": start_date,
            "end_date": end_date,
            "rules": rules_json,
            "metrics": metrics,
            "equity_curve": equity_curve,
            "trades": trades,
        }
