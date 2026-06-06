import pandas as pd
from app.backtesting.indicators import compute_indicators
from app.backtesting.strategy_parser import parse_signals


def test_parse_signals_with_rsi_threshold():
    dates = pd.date_range(start="2024-01-01", periods=60, freq="D")
    df = pd.DataFrame(
        {
            "close": [10 + i * 0.5 for i in range(60)],
            "high": [11 + i * 0.5 for i in range(60)],
            "low": [9 + i * 0.5 for i in range(60)],
            "volume": [1000 + 10 * i for i in range(60)],
        },
        index=dates,
    )

    df = compute_indicators(df)

    rules = {
        "entry": [{"indicator": "RSI", "operator": "<", "value": 50}],
        "exit": [{"indicator": "RSI", "operator": ">", "value": 70}],
    }

    entries, exits = parse_signals(df, rules)

    assert entries.dtype == bool
    assert exits.dtype == bool
    assert len(entries) == len(df)
    assert len(exits) == len(df)
    assert entries.any()
