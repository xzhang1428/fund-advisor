"""Portfolio constraint validation."""

from typing import Optional


class PortfolioConstraints:
    """Define and enforce portfolio allocation constraints."""

    @staticmethod
    def default_constraints(risk_profile: str) -> dict:
        """Get default constraints based on risk profile."""
        constraints = {
            "保守型": {
                "max_single_position": 0.10,   # max 10% in one fund
                "max_stock_exposure": 0.25,    # max 25% in stock/mixed/index
                "max_drawdown_limit": 0.10,    # stop-loss at 10%
                "min_bond_money_exposure": 0.50,  # at least 50% in bonds+money
            },
            "稳健型": {
                "max_single_position": 0.15,
                "max_stock_exposure": 0.55,
                "max_drawdown_limit": 0.15,
                "min_bond_money_exposure": 0.30,
            },
            "平衡型": {
                "max_single_position": 0.20,
                "max_stock_exposure": 0.75,
                "max_drawdown_limit": 0.20,
                "min_bond_money_exposure": 0.15,
            },
            "进取型": {
                "max_single_position": 0.25,
                "max_stock_exposure": 0.95,
                "max_drawdown_limit": 0.25,
                "min_bond_money_exposure": 0.05,
            },
        }
        return constraints.get(risk_profile, constraints["稳健型"])

    @staticmethod
    def validate_allocation(weights: dict, constraints: dict) -> list[str]:
        """
        Validate allocation weights against constraints.
        Returns list of violation messages (empty = all good).
        """
        violations = []

        max_single = constraints.get("max_single_position", 0.2)
        for fund, weight in weights.items():
            if weight > max_single:
                violations.append(f"{fund} 权重 {weight:.1%} 超过上限 {max_single:.1%}")

        stock_cats = ["股票型", "指数型"]
        stock_exposure = sum(w for f, w in weights.items()
                             if any(c in str(f) for c in stock_cats))
        max_stock = constraints.get("max_stock_exposure", 1.0)
        if stock_exposure > max_stock:
            violations.append(f"权益类资产 {stock_exposure:.1%} 超过上限 {max_stock:.1%}")

        bond_cats = ["债券型", "货币型"]
        bond_exposure = sum(w for f, w in weights.items()
                            if any(c in str(f) for c in bond_cats))
        min_bond = constraints.get("min_bond_money_exposure", 0)
        if bond_exposure < min_bond:
            violations.append(f"固收类资产 {bond_exposure:.1%} 低于下限 {min_bond:.1%}")

        return violations
