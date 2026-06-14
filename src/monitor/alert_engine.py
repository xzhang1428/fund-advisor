"""Alert engine that evaluates all rules against current state."""

from datetime import date, datetime
from typing import Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.monitor.rules import ALL_RULES


class AlertEngine:
    """
    Evaluates all alert rules against current portfolio and market state.
    """

    def __init__(self, repository=None):
        self.rules = ALL_RULES
        self.repo = repository

    def check_all(self, context: dict) -> list[dict]:
        """
        Run all rules against the given context.
        Returns list of triggered alerts.
        """
        alerts = []
        for rule in self.rules:
            try:
                result = rule.evaluate(context)
                if result:
                    result["triggered_at"] = datetime.now().isoformat()
                    alerts.append(result)
            except Exception as e:
                print(f"  [Warn] Rule '{rule.rule_id}' failed: {e}")
        return alerts

    def check_and_persist(self, context: dict,
                          portfolio_id: int = None) -> list[dict]:
        """
        Check rules and save alerts to database.
        """
        alerts = self.check_all(context)
        if self.repo:
            for alert in alerts:
                self.repo.add_alert(
                    alert_type=alert.get("alert_type", ""),
                    severity=alert.get("severity", "info"),
                    message=alert.get("message", ""),
                    portfolio_id=portfolio_id,
                    fund_code=alert.get("fund_code"),
                )
            self.repo.commit()
        return alerts

    @staticmethod
    def build_context(portfolio_summary: dict = None,
                      market_data: dict = None,
                      valuation_data: dict = None,
                      index_data: dict = None) -> dict:
        """
        Build the context dictionary for rule evaluation.
        """
        context = {}
        if portfolio_summary:
            context["holdings"] = portfolio_summary.get("holdings", [])
            context["total_return"] = portfolio_summary.get("total_return", 0)
            context["total_value"] = portfolio_summary.get("current_value", 0)
            context["risk_profile"] = portfolio_summary.get("risk_profile", "稳健型")
        if valuation_data:
            context["valuation"] = valuation_data
        if index_data:
            context["index_signals"] = index_data
        if market_data:
            context["market"] = market_data
        return context
