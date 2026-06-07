import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Any


def _safe_float(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        if np.isnan(value):
            return 0.0
    except Exception:
        pass
    return float(value)


def compute_metrics(portfolio: vbt.Portfolio) -> dict:
    trade_df = pd.DataFrame(portfolio.trades.records_readable)
    number_of_trades = int(portfolio.trades.count()) if hasattr(portfolio.trades, "count") else len(trade_df)
    average_trade = 0.0
    if not trade_df.empty and "ReturnPct" in trade_df.columns:
        average_trade = float(trade_df["ReturnPct"].mean() or 0.0)

    win_rate = None
    profit_factor = None
    if hasattr(portfolio.trades, "win_rate"):
        win_rate = portfolio.trades.win_rate()
    if hasattr(portfolio.trades, "profit_factor"):
        profit_factor = portfolio.trades.profit_factor()

    return {
        "total_return": _safe_float(portfolio.total_return()),
        "annualized_return": _safe_float(portfolio.annualized_return()),
        "sharpe_ratio": _safe_float(portfolio.sharpe_ratio()),
        "sortino_ratio": _safe_float(portfolio.sortino_ratio()),
        "max_drawdown": _safe_float(portfolio.max_drawdown()),
        "win_rate": _safe_float(win_rate),
        "profit_factor": _safe_float(profit_factor),
        "average_trade_return": average_trade,
        "number_of_trades": number_of_trades,
    }
