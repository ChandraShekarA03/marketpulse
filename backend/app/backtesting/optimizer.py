import copy
from datetime import datetime
from typing import Any, Dict, List

from app.backtesting.engine import BacktestEngine


class BacktestOptimizer:
    def optimize(
        self,
        base_rules: Dict[str, Any],
        parameter: str,
        lower_bound: float,
        upper_bound: float,
        step: float,
        ticker: str,
        start_date: str,
        end_date: str,
    ) -> Dict[str, Any]:
        if lower_bound >= upper_bound:
            raise ValueError("lower_bound must be less than upper_bound.")

        matching_rules = self._find_parameter_rules(base_rules, parameter)
        if not matching_rules:
            raise ValueError(f"No rules found for parameter: {parameter}")

        engine = BacktestEngine()
        candidates: List[Dict[str, Any]] = []
        value = lower_bound
        while value <= upper_bound + 1e-9:
            rules_copy = copy.deepcopy(base_rules)
            self._update_parameter_rules(rules_copy, parameter, float(value))
            try:
                results = engine.run(
                    rules_json=rules_copy,
                    ticker=ticker,
                    start_date=start_date,
                    end_date=end_date,
                )
                candidates.append(
                    {
                        "value": float(value),
                        "rules": rules_copy,
                        "metrics": results["metrics"],
                    }
                )
            except Exception:
                candidates.append(
                    {
                        "value": float(value),
                        "rules": rules_copy,
                        "metrics": {
                            "sharpe_ratio": 0.0,
                            "total_return": 0.0,
                            "max_drawdown": 0.0,
                        },
                    }
                )
            value += step

        best_by_sharpe = max(candidates, key=lambda candidate: candidate["metrics"].get("sharpe_ratio", 0.0))
        best_by_return = max(candidates, key=lambda candidate: candidate["metrics"].get("total_return", 0.0))
        best_by_drawdown = min(candidates, key=lambda candidate: candidate["metrics"].get("max_drawdown", 0.0))

        return {
            "parameter": parameter,
            "parameter_values_tested": len(candidates),
            "best_by_sharpe": best_by_sharpe,
            "best_by_return": best_by_return,
            "best_by_drawdown": best_by_drawdown,
        }

    def _find_parameter_rules(self, rules_json: Dict[str, Any], parameter: str) -> List[Dict[str, Any]]:
        found = []
        for section in ("entry", "exit"):
            for rule in rules_json.get(section, []):
                if str(rule.get("indicator", "")).strip().lower() == parameter.strip().lower():
                    found.append(rule)
        return found

    def _update_parameter_rules(self, rules_json: Dict[str, Any], parameter: str, value: float):
        for section in ("entry", "exit"):
            for rule in rules_json.get(section, []):
                if str(rule.get("indicator", "")).strip().lower() == parameter.strip().lower():
                    rule["value"] = float(value)
