import pandas as pd
from typing import Any, Dict, List
from app.backtesting.indicators import resolve_indicator_column


VALID_OPERATORS = {"<", ">", "<=", ">=", "==", "!="}


def _build_series(df: pd.DataFrame, rule: Dict[str, Any]) -> pd.Series:
    indicator = rule.get("indicator")
    operator = rule.get("operator")
    value = rule.get("value")

    if indicator is None or operator is None or value is None:
        raise ValueError("Each rule must include indicator, operator, and value.")

    if operator not in VALID_OPERATORS:
        raise ValueError(f"Unsupported operator: {operator}")

    column_name = resolve_indicator_column(indicator, operator)
    if column_name not in df.columns:
        raise ValueError(f"Indicator column not found: {column_name}")

    series = df[column_name].ffill().fillna(0)
    threshold = float(value)

    if operator == "<":
        result = series < threshold
    elif operator == ">":
        result = series > threshold
    elif operator == "<=":
        result = series <= threshold
    elif operator == ">=":
        result = series >= threshold
    elif operator == "==":
        result = series == threshold
    elif operator == "!=":
        result = series != threshold
    else:
        raise ValueError(f"Unsupported operator: {operator}")

    return result.fillna(False)


def _combine_rules(df: pd.DataFrame, rules: List[Dict[str, Any]]) -> pd.Series:
    if not rules:
        return pd.Series(False, index=df.index)

    signals = [_build_series(df, rule) for rule in rules]
    if not signals:
        return pd.Series(False, index=df.index)

    return pd.concat(signals, axis=1).all(axis=1)


def parse_signals(df: pd.DataFrame, rules_json: Dict[str, Any]) -> tuple[pd.Series, pd.Series]:
    entry_rules = rules_json.get("entry", [])
    exit_rules = rules_json.get("exit", [])

    entries = _combine_rules(df, entry_rules)
    exits = _combine_rules(df, exit_rules)

    # Prevent entry and exit firing on the same bar
    exits = exits & ~entries
    return entries.fillna(False), exits.fillna(False)
