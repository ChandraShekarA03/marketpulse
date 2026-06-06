from datetime import datetime, timedelta

import pandas as pd
from app.backtesting.engine import BacktestEngine
from app.services import stock_service


def make_sample_history(days=90):
    start_date = datetime(2023, 1, 1)
    history = []
    for i in range(days):
        date = start_date + timedelta(days=i)
        close = 10 + i * 0.75
        high = close + 0.5
        low = close - 0.5
        open_price = close - 0.25
        history.append(
            {
                "date": date.strftime("%Y-%m-%d"),
                "open": float(open_price),
                "high": float(high),
                "low": float(low),
                "close": float(close),
                "volume": int(1000 + i * 10),
            }
        )
    return history


def test_backtest_engine_generates_metrics(monkeypatch):
    sample_data = make_sample_history()

    def fake_get_historical_data(ticker: str, outputsize: str = "full"):
        assert ticker == "NVDA"
        assert outputsize == "full"
        return sample_data

    monkeypatch.setattr("app.backtesting.engine.get_historical_data", fake_get_historical_data)

    engine = BacktestEngine()
    rules = {
        "entry": [
            {"indicator": "RSI", "operator": "<", "value": 40}
        ],
        "exit": [
            {"indicator": "RSI", "operator": ">", "value": 70}
        ],
    }

    results = engine.run(rules_json=rules, ticker="NVDA", start_date="2023-01-01", end_date="2023-04-30")

    assert results["ticker"] == "NVDA"
    assert results["start_date"] == "2023-01-01"
    assert results["end_date"] == "2023-04-30"
    assert "metrics" in results
    assert results["metrics"]["number_of_trades"] >= 1
    assert isinstance(results["equity_curve"], list)
    assert isinstance(results["trades"], list)
    assert results["metrics"]["total_return"] >= 0.0
