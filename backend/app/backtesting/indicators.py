import pandas as pd
import ta


INDICATOR_MAP = {
    "rsi": "RSI",
    "macd": "MACD",
    "macd_signal": "MACD_signal",
    "sma": "SMA20",
    "ema": "EMA50",
    "bollinger bands": "BB_mid",
    "bollinger bands upper": "BB_high",
    "bollinger bands lower": "BB_low",
    "bb_upper": "BB_high",
    "bb_lower": "BB_low",
    "bb_mid": "BB_mid",
    "atr": "ATR",
    "volume": "volume",
    "close": "close",
}


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df["high"] = pd.to_numeric(df["high"], errors="coerce")
    df["low"] = pd.to_numeric(df["low"], errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce")

    df["RSI"] = ta.momentum.RSIIndicator(close=df["close"], window=14).rsi()
    macd = ta.trend.MACD(close=df["close"])
    df["MACD"] = macd.macd()
    df["MACD_signal"] = macd.macd_signal()

    df["SMA20"] = ta.trend.SMAIndicator(close=df["close"], window=20).sma_indicator()
    df["EMA50"] = ta.trend.EMAIndicator(close=df["close"], window=50).ema_indicator()

    bb = ta.volatility.BollingerBands(close=df["close"], window=20, window_dev=2)
    df["BB_high"] = bb.bollinger_hband()
    df["BB_low"] = bb.bollinger_lband()
    df["BB_mid"] = bb.bollinger_mavg()

    df["ATR"] = ta.volatility.AverageTrueRange(
        high=df["high"], low=df["low"], close=df["close"], window=14
    ).average_true_range()

    return df


def resolve_indicator_column(indicator: str, operator: str) -> str:
    normalized = (indicator or "").strip().lower()
    if normalized in INDICATOR_MAP:
        return INDICATOR_MAP[normalized]

    if normalized == "bollinger bands":
        return "BB_low" if operator in ("<", "<=") else "BB_high"

    if normalized.startswith("bollinger"):
        if "upper" in normalized:
            return "BB_high"
        if "lower" in normalized:
            return "BB_low"
        return "BB_mid"

    if normalized == "sma":
        return "SMA20"
    if normalized == "ema":
        return "EMA50"
    if normalized == "macd":
        return "MACD"
    if normalized == "volume":
        return "volume"

    raise ValueError(f"Unsupported indicator: {indicator}")
