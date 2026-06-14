"""Portfolio rebalancing logic."""

from typing import Optional
from datetime import date, datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import REBALANCE_THRESHOLD


class RebalanceEngine:
    """Compute rebalancing trades to bring portfolio back to target allocation."""

    def __init__(self, threshold: float = None):
        self.threshold = threshold or REBALANCE_THRESHOLD

    def need_rebalance(self, allocation_diff: dict) -> bool:
        """
        Check if any category drift exceeds threshold.
        """
        for cat, diff in allocation_diff.items():
            if abs(diff.get("drift", 0)) > self.threshold:
                return True
        return False

    def compute_rebalance_trades(self, portfolio_summary: dict) -> list[dict]:
        """
        Compute trades needed to rebalance to target allocation.
        Returns list of trade suggestions.
        """
        total_value = portfolio_summary.get("current_value", 0)
        if total_value <= 0:
            return []

        alloc_diff = portfolio_summary.get("allocation_diff", {})
        trades = []

        for category, diff_info in alloc_diff.items():
            drift = diff_info.get("drift", 0)
            actual = diff_info.get("actual", 0)
            target = diff_info.get("target", 0)

            if abs(drift) <= self.threshold:
                continue

            target_value = total_value * target
            current_value = total_value * actual
            trade_amount = target_value - current_value

            if trade_amount > 0:
                action = "买入"
                trade_type = "BUY"
            else:
                action = "卖出"
                trade_type = "SELL"

            trades.append({
                "category": category,
                "action": action,
                "trade_type": trade_type,
                "trade_amount": abs(trade_amount),
                "current_weight": actual,
                "target_weight": target,
                "drift": drift,
            })

        # Sort: sells first (to raise cash), then buys
        return sorted(trades, key=lambda t: 0 if t["trade_type"] == "SELL" else 1)

    def compute_fund_level_trades(self, portfolio_summary: dict,
                                  recommendations: list[dict]) -> list[dict]:
        """
        Compute specific fund-level trades based on recommendations.
        """
        trades = []
        for rec in recommendations:
            signal = rec.get("signal_enum")
            weight = rec.get("weight", 0)

            if signal is None:
                continue

            signal_val = signal.value if hasattr(signal, 'value') else str(signal)

            if signal_val in ["卖出", "SELL"] and weight > 0.01:
                trades.append({
                    "fund_code": rec.get("fund_code"),
                    "fund_name": rec.get("fund_name"),
                    "action": "卖出全部",
                    "reason": f"评分低({rec.get('score', 0)})，建议清仓",
                    "current_weight": weight,
                })
            elif signal_val in ["减仓", "REDUCE"] and weight > 0.02:
                target_weight = weight * 0.5  # reduce by half
                trades.append({
                    "fund_code": rec.get("fund_code"),
                    "fund_name": rec.get("fund_name"),
                    "action": f"减仓至{target_weight:.1%}",
                    "reason": f"评分偏低({rec.get('score', 0)})，建议减半仓",
                    "current_weight": weight,
                })
            elif signal_val in ["加仓", "ACCUMULATE"] and weight < 0.15:
                target_weight = min(weight * 1.5, 0.15)
                trades.append({
                    "fund_code": rec.get("fund_code"),
                    "fund_name": rec.get("fund_name"),
                    "action": f"加仓至{target_weight:.1%}",
                    "reason": f"评分较高({rec.get('score', 0)})，建议增持",
                    "current_weight": weight,
                })

        return trades

    @staticmethod
    def estimate_redemption_fee(holding_days: int) -> float:
        """
        Estimate redemption fee based on holding period.
        Chinese fund standards:
        < 7 days: 1.5%
        < 30 days: 0.75%
        < 365 days: 0.5%
        < 730 days: 0.25%
        >= 730 days: 0%
        """
        if holding_days < 7:
            return 0.015
        elif holding_days < 30:
            return 0.0075
        elif holding_days < 365:
            return 0.005
        elif holding_days < 730:
            return 0.0025
        else:
            return 0.0

    @staticmethod
    def format_rebalance_report(trades: list[dict]) -> str:
        """Format rebalancing trades as a readable report."""
        if not trades:
            return "[OK] 当前持仓未触发调仓阈值，无需再平衡。"

        lines = ["=" * 60, "  组合再平衡建议", "=" * 60, ""]

        total_buy = sum(t["trade_amount"] for t in trades
                        if t.get("trade_type") == "BUY")
        total_sell = sum(t["trade_amount"] for t in trades
                         if t.get("trade_type") == "SELL")

        for t in trades:
            trade_amount = t.get("trade_amount")
            if trade_amount:
                lines.append(
                    f"  {'[BUY]' if t.get('trade_type') == 'BUY' else '[SELL]'} "
                    f"{t.get('action', '')} {t.get('category', '')}: "
                    f"CNY{trade_amount:,.2f}"
                )
                lines.append(
                    f"     当前权重: {t.get('current_weight', 0):.1%} → "
                    f"目标权重: {t.get('target_weight', 0):.1%} "
                    f"(偏差: {t.get('drift', 0):.1%})"
                )
            else:
                lines.append(f"  → {t.get('action', '')} {t.get('fund_name', t.get('fund_code', ''))}: {t.get('reason', '')}")
            lines.append("")

        if total_sell > 0 or total_buy > 0:
            lines.append(f"  Total Sell: CNY{total_sell:,.2f}")
            lines.append(f"  Total Buy:  CNY{total_buy:,.2f}")
            lines.append(f"  Net Flow:   CNY{total_buy - total_sell:,.2f}")

        lines.append("=" * 60)
        return "\n".join(lines)
