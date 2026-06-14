"""Portfolio management - create, track, and manage investment portfolios."""

from datetime import date, datetime
from typing import Optional, List
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.storage.repository import Repository
from src.storage.models import Portfolio, Holding, Transaction, FundBasicInfo, FundNav
from config.settings import RiskProfile, RISK_ALLOCATIONS


class PortfolioManager:
    """Manage investment portfolios and holdings."""

    def __init__(self, repo: Repository):
        self.repo = repo

    def create_portfolio(self, name: str, initial_capital: float,
                         risk_profile: str = "稳健型",
                         description: str = None) -> Portfolio:
        """
        Create a new portfolio with default allocation plan.
        Args:
            name: Portfolio name
            initial_capital: Total capital in CNY
            risk_profile: One of 保守型/稳健型/平衡型/进取型
            description: Optional notes
        """
        portfolio = self.repo.create_portfolio(
            name=name,
            initial_capital=initial_capital,
            risk_profile=risk_profile,
            description=description,
        )

        # Create default allocation plan from risk profile
        alloc_template = RISK_ALLOCATIONS.get(risk_profile, RISK_ALLOCATIONS["稳健型"])
        for category, target_weight in alloc_template.items():
            if target_weight > 0:
                from src.storage.models import AllocationPlan
                plan = AllocationPlan(
                    portfolio_id=portfolio.id,
                    category=category,
                    target_weight=target_weight,
                    max_weight=min(target_weight * 1.3, 0.5),
                    min_weight=max(target_weight * 0.5, 0.01),
                )
                self.repo.session.add(plan)

        self.repo.commit()
        print(f"  Portfolio '{name}' created (ID: {portfolio.id}), "
              f"Capital: CNY{initial_capital:,.2f}, Risk: {risk_profile}")
        return portfolio

    def add_holding(self, portfolio_id: int, fund_code: str,
                    shares: float, avg_cost: float,
                    purchase_date: date = None, notes: str = None):
        """Add or increase a holding. Records the transaction."""
        if purchase_date is None:
            purchase_date = date.today()

        # Record transaction
        amount = shares * avg_cost
        self.repo.add_transaction(
            portfolio_id=portfolio_id,
            fund_code=fund_code,
            transaction_type="BUY",
            transaction_date=purchase_date,
            shares=shares,
            price=avg_cost,
            amount=amount,
            notes=notes,
        )

        # Update holdings
        self.repo.add_holding(
            portfolio_id=portfolio_id,
            fund_code=fund_code,
            shares=shares,
            avg_cost=avg_cost,
            purchase_date=purchase_date,
            notes=notes,
        )
        self.repo.commit()

    def sell_holding(self, portfolio_id: int, fund_code: str,
                     shares: float, price: float,
                     sell_date: date = None, notes: str = None):
        """Sell (reduce) a holding. Records the transaction."""
        if sell_date is None:
            sell_date = date.today()

        holding = self.repo.session.query(Holding).filter(
            Holding.portfolio_id == portfolio_id,
            Holding.fund_code == fund_code,
        ).first()

        if not holding:
            print(f"  [Error] No holding found for fund {fund_code} in portfolio {portfolio_id}")
            return

        if shares > holding.shares:
            print(f"  [Warn] Selling {shares} but only have {holding.shares}. Selling all.")
            shares = holding.shares

        amount = shares * price

        # Record transaction
        self.repo.add_transaction(
            portfolio_id=portfolio_id,
            fund_code=fund_code,
            transaction_type="SELL",
            transaction_date=sell_date,
            shares=shares,
            price=price,
            amount=amount,
            notes=notes,
        )

        # Update holdings
        self.repo.remove_holding(portfolio_id, fund_code, shares)
        self.repo.commit()
        print(f"  Sold {shares:.2f} shares of {fund_code} at CNY{price:.4f}, "
              f"Total: CNY{amount:,.2f}")

    def update_nav(self, portfolio_id: int, fund_code: str,
                   nav: float, update_date: date = None):
        """Update latest NAV for a holding."""
        if update_date is None:
            update_date = date.today()
        self.repo.update_holding_nav(portfolio_id, fund_code, nav, update_date)
        self.repo.commit()

    def get_portfolio_summary(self, portfolio_id: int) -> dict:
        """
        Get comprehensive portfolio summary.
        Returns dict with total_value, pnl, holdings details, allocation breakdown.
        """
        portfolio = self.repo.get_portfolio(portfolio_id)
        if not portfolio:
            return {"error": f"Portfolio {portfolio_id} not found"}

        holdings = self.repo.get_portfolio_holdings(portfolio_id)

        total_market_value = 0.0
        total_cost = 0.0
        holding_details = []

        for h in holdings:
            nav = h.last_nav or h.avg_cost
            market_value = h.shares * nav
            cost = h.shares * h.avg_cost
            pnl = market_value - cost
            pnl_pct = (nav / h.avg_cost - 1) if h.avg_cost > 0 else 0

            total_market_value += market_value
            total_cost += cost

            # Get fund name
            fund_info = self.repo.get_fund_info(h.fund_code)
            fund_name = fund_info.fund_name if fund_info else h.fund_code
            fund_type = fund_info.fund_type if fund_info else "未知"

            holding_details.append({
                "fund_code": h.fund_code,
                "fund_name": fund_name,
                "fund_type": fund_type,
                "shares": h.shares,
                "avg_cost": h.avg_cost,
                "current_nav": nav,
                "market_value": market_value,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "weight": 0.0,  # computed below
                "purchase_date": str(h.purchase_date) if h.purchase_date else None,
            })

        # Compute weights
        if total_market_value > 0:
            for hd in holding_details:
                hd["weight"] = hd["market_value"] / total_market_value

        total_pnl = total_market_value - total_cost
        total_return = (total_market_value / total_cost - 1) if total_cost > 0 else 0

        # Allocation breakdown
        allocation = {}
        for hd in holding_details:
            cat = hd["fund_type"]
            allocation[cat] = allocation.get(cat, 0) + hd["weight"]

        # Compare with target allocation
        target_alloc = {}
        from src.storage.models import AllocationPlan
        plans = self.repo.session.query(AllocationPlan).filter(
            AllocationPlan.portfolio_id == portfolio_id
        ).all()
        for plan in plans:
            target_alloc[plan.category] = plan.target_weight

        allocation_diff = {}
        for cat in set(list(allocation.keys()) + list(target_alloc.keys())):
            actual = allocation.get(cat, 0)
            target = target_alloc.get(cat, 0)
            allocation_diff[cat] = {
                "actual": actual,
                "target": target,
                "drift": actual - target,
            }

        return {
            "portfolio_name": portfolio.name,
            "risk_profile": portfolio.risk_profile,
            "initial_capital": portfolio.initial_capital,
            "current_value": total_market_value,
            "total_cost": total_cost,
            "total_pnl": total_pnl,
            "total_return": total_return,
            "holdings": holding_details,
            "allocation": allocation,
            "target_allocation": target_alloc,
            "allocation_diff": allocation_diff,
            "holdings_count": len(holding_details),
            "created_at": str(portfolio.created_at),
        }

    def check_constraints(self, portfolio_id: int) -> list[str]:
        """Check if portfolio violates any constraints. Returns list of warnings."""
        warnings = []
        summary = self.get_portfolio_summary(portfolio_id)
        if "error" in summary:
            return warnings

        # Check single position limits (max 20% of portfolio)
        for h in summary["holdings"]:
            if h["weight"] > 0.20:
                warnings.append(f"[!] {h['fund_name']}({h['fund_code']}) 占比 "
                              f"{h['weight']:.1%}，超过20%单只基金上限")

        # Check category exposure limits
        for cat, diff in summary["allocation_diff"].items():
            if abs(diff["drift"]) > 0.10:
                direction = "超配" if diff["drift"] > 0 else "低配"
                warnings.append(f"[!] {cat} {direction} {abs(diff['drift']):.1%}，"
                              f"目标 {diff['target']:.1%}，实际 {diff['actual']:.1%}")

        # Check drawdown
        for h in summary["holdings"]:
            if h["pnl_pct"] < -0.10:
                warnings.append(f"[STOP] {h['fund_name']}({h['fund_code']}) 亏损 "
                              f"{h['pnl_pct']:.1%}，触发10%止损预警")

        return warnings

    def get_portfolio_history(self, portfolio_id: int) -> list:
        """Get transaction history for a portfolio."""
        return self.repo.get_transactions(portfolio_id=portfolio_id)

    def delete_portfolio(self, portfolio_id: int):
        """Soft-delete a portfolio (mark inactive)."""
        portfolio = self.repo.get_portfolio(portfolio_id)
        if portfolio:
            portfolio.is_active = False
            self.repo.commit()
            print(f"  Portfolio '{portfolio.name}' (ID: {portfolio_id}) deactivated.")
