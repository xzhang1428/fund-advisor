"""Buy/Sell/Hold signal generation for funds and portfolios."""

from typing import Optional, List
from datetime import date
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import Signal, MarketRegime, FundCategory


class SignalGenerator:
    """
    Generate actionable buy/sell/hold signals for funds.
    Combines scoring, market regime, valuation, and portfolio context.
    """

    def __init__(self, scorer, market_regime: MarketRegime = MarketRegime.SIDEWAYS,
                 valuation_data: dict = None):
        """
        Args:
            scorer: MultiFactorScorer instance
            market_regime: Current market regime
            valuation_data: {index_symbol: pe_percentile, ...}
        """
        self.scorer = scorer
        self.regime = market_regime
        self.valuation_data = valuation_data or {}

    def generate_signal(self, fund_data: dict,
                        in_holdings: bool = False,
                        holding_pnl_pct: float = 0.0) -> dict:
        """
        Generate a signal for a single fund.
        Returns dict with signal, confidence, rationale.
        """
        score = fund_data.get("total_score", 0)
        if isinstance(score, dict):
            score = score.get("total_score", 0)

        category = fund_data.get("fund_type", "混合型")
        is_index_fund = (category == "指数型")

        signal = Signal.HOLD
        confidence = 0.5
        rationale = []

        # --- Decision Logic ---

        # Score >= 70: Consider buying or accumulating
        if score >= 70:
            # Strong buy conditions
            if self.regime == MarketRegime.BULL and category in ["股票型", "指数型", "混合型"]:
                signal = Signal.BUY
                confidence = 0.85
                rationale.append(f"高评分({score}) + 牛市环境，权益类资产受益")
            elif is_index_fund and self._is_undervalued():
                signal = Signal.BUY
                confidence = 0.80
                rationale.append(f"高评分({score}) + 指数估值低位，价值买入机会")
            elif self.regime == MarketRegime.SIDEWAYS and category in ["指数型", "混合型"]:
                signal = Signal.BUY
                confidence = 0.65
                rationale.append(f"高评分({score}) + 震荡市适合定投布局")
            else:
                signal = Signal.ACCUMULATE
                confidence = 0.60
                rationale.append(f"高评分({score})，但市场环境不是最佳买入时机，建议分批加仓")

        # Score 50-70: Hold
        elif score >= 50:
            signal = Signal.HOLD
            confidence = 0.60
            rationale.append(f"评分中等({score})，建议继续持有观察")

        # Score 30-50: Consider reducing if held
        elif score >= 30:
            if in_holdings:
                signal = Signal.REDUCE
                confidence = 0.55
                rationale.append(f"评分偏低({score})，建议适当减仓")
            else:
                signal = Signal.HOLD
                confidence = 0.50
                rationale.append(f"评分偏低({score})，不建议买入")

        # Score < 30: Strong sell if held
        else:
            if in_holdings:
                signal = Signal.SELL
                confidence = 0.80
                rationale.append(f"评分很低({score})，建议卖出")
            else:
                signal = Signal.HOLD
                confidence = 0.70
                rationale.append(f"评分很低({score})，不建议买入")

        # --- Override Rules ---

        # Stop-loss override
        if in_holdings and holding_pnl_pct < -0.15:
            signal = Signal.SELL
            confidence = max(confidence, 0.90)
            rationale.append("[STOP] 触发止损线：亏损超过15%，强制卖出信号")

        # Manager change override (reduces confidence)
        manager_tenure = fund_data.get("manager_tenure_days", 365)
        if manager_tenure is not None and manager_tenure < 90:
            confidence *= 0.7
            rationale.append("[!] 基金经理近期变更(任职<90天)，信号置信度降低")

        # Valuation extreme override for index funds
        if is_index_fund:
            pe_pct = fund_data.get("pe_percentile", 50)
            if pe_pct > 80 and signal in [Signal.BUY, Signal.ACCUMULATE]:
                signal = Signal.HOLD
                rationale.append("[!] 估值处于历史高位(>80%分位)，暂缓买入")
                confidence *= 0.7
            elif pe_pct < 20 and signal in [Signal.SELL, Signal.REDUCE]:
                signal = Signal.HOLD
                rationale.append("[i] 估值处于历史低位(<20%分位)，不建议卖出")
                confidence *= 0.6

        return {
            "fund_code": fund_data.get("fund_code", ""),
            "signal": signal.value,
            "signal_enum": signal,
            "confidence": round(confidence, 2),
            "score": score,
            "rationale": rationale,
        }

    def generate_portfolio_signals(self, portfolio_summary: dict) -> list[dict]:
        """
        Generate signals for all holdings in a portfolio.
        """
        signals = []
        for holding in portfolio_summary.get("holdings", []):
            fund_data = {
                "fund_code": holding.get("fund_code"),
                "fund_name": holding.get("fund_name"),
                "fund_type": holding.get("fund_type"),
                "total_score": holding.get("total_score", 50),
            }
            signal = self.generate_signal(
                fund_data,
                in_holdings=True,
                holding_pnl_pct=holding.get("pnl_pct", 0),
            )
            signal["fund_name"] = holding.get("fund_name", "")
            signal["pnl_pct"] = holding.get("pnl_pct", 0)
            signal["weight"] = holding.get("weight", 0)
            signals.append(signal)

        return sorted(signals, key=lambda s: (
            0 if s["signal_enum"] == Signal.SELL else
            1 if s["signal_enum"] == Signal.REDUCE else
            2 if s["signal_enum"] == Signal.HOLD else
            3 if s["signal_enum"] == Signal.ACCUMULATE else
            4
        ))

    def _is_undervalued(self) -> bool:
        """Check if overall market appears undervalued."""
        if not self.valuation_data:
            return False
        # Check major indices
        pe_values = self.valuation_data.values()
        if not pe_values:
            return False
        avg_pe_pct = sum(pe_values) / len(pe_values)
        return avg_pe_pct < 35

    @staticmethod
    def signal_to_emoji(signal: Signal) -> str:
        """Get indicator for signal."""
        return {
            Signal.BUY: "[BUY]",
            Signal.ACCUMULATE: "[ACC]",
            Signal.HOLD: "[HLD]",
            Signal.REDUCE: "[RED]",
            Signal.SELL: "[SEL]",
        }.get(signal, "[-]")

    @staticmethod
    def format_signal_report(signals: list[dict]) -> str:
        """Format signals into a readable report."""
        lines = ["=" * 60, "  基金交易信号报告", "=" * 60, ""]
        for s in signals:
            emoji = SignalGenerator.signal_to_emoji(s.get("signal_enum", Signal.HOLD))
            lines.append(
                f"{emoji} {s.get('fund_name', s.get('fund_code', ''))} "
                f"({s.get('fund_code', '')})"
            )
            lines.append(f"   信号: {s.get('signal', '持有')} | "
                         f"评分: {s.get('score', 0):.0f} | "
                         f"置信度: {s.get('confidence', 0):.0%}")
            if s.get("pnl_pct"):
                sign = "+" if s["pnl_pct"] >= 0 else ""
                lines.append(f"   盈亏: {sign}{s['pnl_pct']:.1%} | "
                             f"仓位: {s.get('weight', 0):.1%}")
            if s.get("rationale"):
                for r in s["rationale"]:
                    lines.append(f"   → {r}")
            lines.append("")
        return "\n".join(lines)
