"""Alert rules for Chinese fund investment risk monitoring.

Design principle: Different fund types have fundamentally different risk profiles.
A 10% drop in a stock fund is normal; a 3% drop in a bond fund may signal credit default.
"""

from datetime import date, datetime, timedelta
from typing import Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class AlertRule:
    """Base class for alert rules."""
    def __init__(self, rule_id: str, name: str, severity: str = "warning", description: str = ""):
        self.rule_id = rule_id
        self.name = name
        self.severity = severity
        self.description = description

    def evaluate(self, context: dict) -> Optional[dict]:
        raise NotImplementedError


# ============================================================
# Helper: get fund-type-aware thresholds
# ============================================================
def _get_fund_type(h: dict) -> str:
    """Extract fund type from holding dict."""
    return h.get("fund_type", "混合型")


def _drawdown_threshold(fund_type: str) -> tuple:
    """Returns (warning_pct, critical_pct) for drawdown based on fund type."""
    if "债券" in fund_type:
        return (-0.03, -0.06)    # 债券亏损3%就严重了
    elif "货币" in fund_type:
        return (-0.005, -0.01)   # 货币基金几乎不该亏损
    elif "指数" in fund_type:
        return (-0.12, -0.20)    # 指数基金波动较大
    elif "股票" in fund_type:
        return (-0.12, -0.20)    # 股票基金波动大
    elif "QDII" in fund_type:
        return (-0.12, -0.18)    # QDII有汇率叠加
    else:
        return (-0.08, -0.15)    # 混合型居中


# ============================================================
# Rule 1: Fund Drawdown (type-aware)
# ============================================================
class DrawdownRule(AlertRule):
    """Alert when a fund's loss exceeds type-appropriate thresholds."""

    def __init__(self):
        super().__init__("fund_drawdown", "持仓亏损告警", "warning",
                         "根据基金类型设定差异化亏损阈值")

    def evaluate(self, context: dict) -> Optional[dict]:
        holdings = context.get("holdings", [])
        if not holdings:
            return None
        results = []
        for h in holdings:
            pnl_pct = h.get("pnl_pct", 0)
            ftype = _get_fund_type(h)
            warn_pct, crit_pct = _drawdown_threshold(ftype)
            if pnl_pct <= crit_pct:
                results.append({
                    "rule_id": self.rule_id, "alert_type": self.name,
                    "severity": "critical", "fund_code": h.get("fund_code"),
                    "message": (
                        f"🔴 {h.get('fund_name', h.get('fund_code'))} ({ftype}) "
                        f"亏损 {pnl_pct*100:.1f}%，超过{ftype}严重线 {abs(crit_pct)*100:.0f}%。"
                        f"请评估是否继续持有或止损。"
                    ),
                })
            elif pnl_pct <= warn_pct:
                results.append({
                    "rule_id": self.rule_id, "alert_type": self.name,
                    "severity": "warning", "fund_code": h.get("fund_code"),
                    "message": (
                        f"🟡 {h.get('fund_name', h.get('fund_code'))} ({ftype}) "
                        f"亏损 {pnl_pct*100:.1f}%，超过{ftype}警戒线 {abs(warn_pct)*100:.0f}%。"
                        f"建议关注，若继续扩大考虑减仓。"
                    ),
                })
        return results[0] if results else None


# ============================================================
# Rule 2: Portfolio Drawdown (risk-profile-aware)
# ============================================================
class PortfolioDrawdownRule(AlertRule):
    """Overall portfolio drawdown, threshold varies by risk profile."""

    def __init__(self):
        super().__init__("portfolio_drawdown", "组合整体回撤告警", "critical",
                         "不同风险偏好的组合有不同的回撤容忍度")

    def evaluate(self, context: dict) -> Optional[dict]:
        total_return = context.get("total_return", 0)
        risk_profile = context.get("risk_profile", "稳健型")

        # Different profiles tolerate different drawdowns
        thresholds = {
            "保守型": (-0.05, -0.08),
            "稳健型": (-0.08, -0.12),
            "平衡型": (-0.12, -0.18),
            "进取型": (-0.18, -0.25),
        }
        warn_pct, crit_pct = thresholds.get(risk_profile, (-0.10, -0.15))

        if total_return <= crit_pct:
            return {
                "rule_id": self.rule_id, "alert_type": self.name,
                "severity": "critical",
                "message": (
                    f"🔴 组合整体亏损 {total_return*100:.1f}%，超过{risk_profile}严重线 {abs(crit_pct)*100:.0f}%。"
                    f"强烈建议全面审视持仓，考虑系统性减仓。"
                    f"记住：亏损 {abs(total_return*100):.0f}% 需要涨 {abs(total_return/(1+total_return))*100:.0f}% 才能回本。"
                ),
            }
        elif total_return <= warn_pct:
            return {
                "rule_id": self.rule_id, "alert_type": self.name,
                "severity": "warning",
                "message": (
                    f"🟡 组合整体亏损 {total_return*100:.1f}%，超过{risk_profile}警戒线 {abs(warn_pct)*100:.0f}%。"
                    f"检查是否有个别持仓跌幅过大，考虑减仓高风险品种。"
                ),
            }
        return None


# ============================================================
# Rule 3: Consecutive Decline (阴跌比急跌更可怕)
# ============================================================
class ConsecutiveDeclineRule(AlertRule):
    """Alert when a fund has been declining for multiple consecutive periods."""

    def __init__(self):
        super().__init__("consecutive_decline", "连续下跌告警", "warning",
                         "阴跌不止往往比单日暴跌更具杀伤力，说明趋势已坏")

    def evaluate(self, context: dict) -> Optional[dict]:
        holdings = context.get("holdings", [])
        results = []
        for h in holdings:
            consecutive = h.get("consecutive_decline_days", 0)
            if consecutive >= 5:
                results.append({
                    "rule_id": self.rule_id, "alert_type": self.name,
                    "severity": "warning" if consecutive < 8 else "critical",
                    "fund_code": h.get("fund_code"),
                    "message": (
                        f"{'🔴' if consecutive >= 8 else '🟡'} {h.get('fund_name', h.get('fund_code'))} "
                        f"连续下跌 {consecutive} 天。阴跌往往被忽视但伤害极大——"
                        f"不要因为每天跌幅小就掉以轻心，这可能是趋势性转弱的信号。"
                    ),
                })
        return results[0] if results else None


# ============================================================
# Rule 4: Single-Day Crash (黑天鹅检测)
# ============================================================
class SingleDayCrashRule(AlertRule):
    """Alert on single-day crash exceeding fund-type appropriate threshold."""

    def __init__(self):
        super().__init__("single_day_crash", "单日暴跌告警", "critical",
                         "单日跌幅异常可能意味着持仓踩雷或黑天鹅事件")

    def evaluate(self, context: dict) -> Optional[dict]:
        holdings = context.get("holdings", [])
        results = []
        for h in holdings:
            daily_drop = h.get("latest_daily_return", 0)
            ftype = _get_fund_type(h)
            # Threshold by type: bond >2% is huge, stock >5% is notable, >7% is alarming
            if "债券" in ftype and daily_drop < -0.02:
                results.append({
                    "rule_id": self.rule_id, "alert_type": self.name,
                    "severity": "critical", "fund_code": h.get("fund_code"),
                    "message": (
                        f"🔴 {h.get('fund_name', h.get('fund_code'))} ({ftype}) "
                        f"单日跌 {daily_drop*100:.1f}%！债券基金单日跌幅超2%极不寻常，"
                        f"可能持仓中有债券违约或信用风险事件，建议立即排查。"
                    ),
                })
            elif daily_drop < -0.07:
                results.append({
                    "rule_id": self.rule_id, "alert_type": self.name,
                    "severity": "critical" if daily_drop < -0.09 else "warning",
                    "fund_code": h.get("fund_code"),
                    "message": (
                        f"{'🔴' if daily_drop < -0.09 else '🟡'} {h.get('fund_name', h.get('fund_code'))} ({ftype}) "
                        f"单日暴跌 {daily_drop*100:.1f}%。{'这种级别的跌幅通常伴随重大利空，' if daily_drop < -0.09 else ''}"
                        f"不要急于抄底——等企稳信号出现后再评估。"
                    ),
                })
        return results[0] if results else None


# ============================================================
# Rule 5: Fund Size Warning (清盘风险)
# ============================================================
class FundSizeWarningRule(AlertRule):
    """Alert when fund AUM is too small (liquidation risk) or too large."""

    def __init__(self):
        super().__init__("fund_size", "基金规模异常告警", "warning",
                         "规模过小有清盘风险，规模过大可能影响收益")

    def evaluate(self, context: dict) -> Optional[dict]:
        holdings = context.get("holdings", [])
        results = []
        for h in holdings:
            aum = h.get("aum_yuan", None)  # in 亿元
            if aum is None:
                continue
            if aum < 0.5:  # < 5000万
                results.append({
                    "rule_id": self.rule_id, "alert_type": self.name,
                    "severity": "critical", "fund_code": h.get("fund_code"),
                    "message": (
                        f"🔴 {h.get('fund_name', h.get('fund_code'))} 规模仅 {aum*100:.0f} 万，"
                        f"低于5000万清盘红线！根据规定，连续60日规模低于5000万可能触发清盘。"
                        f"建议尽快赎回，避免被动清盘造成的流动性损失。"
                    ),
                })
            elif aum < 1.0:  # < 1亿
                results.append({
                    "rule_id": self.rule_id, "alert_type": self.name,
                    "severity": "warning", "fund_code": h.get("fund_code"),
                    "message": (
                        f"🟡 {h.get('fund_name', h.get('fund_code'))} 规模仅 {aum:.2f} 亿，"
                        f"偏小。规模小于1亿的基金有清盘风险，且运作成本占比高，建议关注。"
                    ),
                })
        return results[0] if results else None


# ============================================================
# Rule 6: Sector Concentration (行业集中度)
# ============================================================
class SectorConcentrationRule(AlertRule):
    """Alert when too many holdings are in the same sector/industry."""

    def __init__(self):
        super().__init__("sector_concentration", "行业集中度告警", "warning",
                         "多只基金重仓同一行业，一旦该行业下跌将产生共振亏损")

    def evaluate(self, context: dict) -> Optional[dict]:
        holdings = context.get("holdings", [])
        if not holdings:
            return None

        # Count by fund type as proxy for sector/strategy concentration
        type_counts = {}
        for h in holdings:
            ftype = _get_fund_type(h)
            weight = h.get("weight", 0)
            type_counts[ftype] = type_counts.get(ftype, 0) + weight

        for ftype, total_weight in type_counts.items():
            if ftype in ("股票型", "指数型") and total_weight > 0.60:
                return {
                    "rule_id": self.rule_id, "alert_type": self.name,
                    "severity": "warning",
                    "message": (
                        f"🟡 权益类基金（股票型+指数型）合计占比 {total_weight:.0%}，"
                        f"超过60%。如果市场整体下跌，你的组合将缺乏对冲手段。"
                        f"建议增加债券型或货币型基金来降低整体波动。"
                    ),
                }
        return None


# ============================================================
# Rule 7: Holding Period Alert (赎回费提醒)
# ============================================================
class HoldingPeriodRule(AlertRule):
    """Remind about redemption fees when selling funds held < 7 or < 30 days."""

    def __init__(self):
        super().__init__("holding_period", "短期赎回费提醒", "info",
                         "持有不足7天赎回费率1.5%，不足30天0.5%-0.75%，交易成本极高")

    def evaluate(self, context: dict) -> Optional[dict]:
        holdings = context.get("holdings", [])
        results = []
        for h in holdings:
            purchase_date = h.get("purchase_date")
            if not purchase_date:
                continue
            try:
                if isinstance(purchase_date, str):
                    pd_date = date.fromisoformat(purchase_date)
                else:
                    pd_date = purchase_date
                days = (date.today() - pd_date).days
            except Exception:
                continue

            if days < 7:
                results.append({
                    "rule_id": self.rule_id, "alert_type": self.name,
                    "severity": "warning", "fund_code": h.get("fund_code"),
                    "message": (
                        f"⚠ {h.get('fund_name', h.get('fund_code'))} 持有仅 {days} 天，"
                        f"如果现在赎回将收取 1.5% 惩罚性赎回费（持有不足7天）。"
                        f"强烈建议至少持有7天以上再考虑卖出。"
                    ),
                })
            elif days < 30:
                results.append({
                    "rule_id": self.rule_id, "alert_type": self.name,
                    "severity": "info", "fund_code": h.get("fund_code"),
                    "message": (
                        f"💡 {h.get('fund_name', h.get('fund_code'))} 持有 {days} 天，"
                        f"赎回费率约 0.5%-0.75%。建议持有满30天以上费率会进一步降低。"
                    ),
                })
        return results[0] if results else None


# ============================================================
# Rule 8: No Bond/Money Buffer (缺乏防御资产)
# ============================================================
class NoDefenseBufferRule(AlertRule):
    """Alert when portfolio lacks defensive assets (bonds/money market)."""

    def __init__(self):
        super().__init__("no_defense", "缺乏防御资产告警", "warning",
                         "组合中没有债券或货币基金作为缓冲，市场下跌时没有避险手段")

    def evaluate(self, context: dict) -> Optional[dict]:
        holdings = context.get("holdings", [])
        if not holdings:
            return None

        defense_weight = sum(
            h.get("weight", 0) for h in holdings
            if "债券" in _get_fund_type(h) or "货币" in _get_fund_type(h)
        )
        equity_weight = sum(
            h.get("weight", 0) for h in holdings
            if "股票" in _get_fund_type(h) or "指数" in _get_fund_type(h)
        )

        if equity_weight > 0.70 and defense_weight < 0.10:
            return {
                "rule_id": self.rule_id, "alert_type": self.name,
                "severity": "warning",
                "message": (
                    f"🟡 权益类仓位高达 {equity_weight:.0%}，但防御资产仅 {defense_weight:.0%}。"
                    f"一旦市场大跌，组合将面临较大回撤且没有缓冲。"
                    f"建议至少配置 10-20% 的债券或货币基金作为安全垫。"
                ),
            }
        return None


# ============================================================
# All rules registry
# ============================================================
ALL_RULES = [
    DrawdownRule(),              # 1. 类型感知的亏损告警
    SingleDayCrashRule(),        # 2. 单日暴跌（黑天鹅）
    ConsecutiveDeclineRule(),    # 3. 连续下跌（阴跌）
    PortfolioDrawdownRule(),     # 4. 组合整体回撤
    FundSizeWarningRule(),       # 5. 规模异常/清盘风险
    SectorConcentrationRule(),   # 6. 行业/类型过度集中
    NoDefenseBufferRule(),       # 7. 缺乏防御资产
    HoldingPeriodRule(),         # 8. 短期赎回费提醒
]
