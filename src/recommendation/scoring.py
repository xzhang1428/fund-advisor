"""Multi-factor fund scoring model."""

import numpy as np
import pandas as pd
from typing import Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import SCORING_WEIGHTS, MarketRegime


class MultiFactorScorer:
    """
    Score funds on 0-100 scale using multiple factors.
    Higher score = better investment.
    """

    def __init__(self, config: dict = None):
        self.config = config or SCORING_WEIGHTS
        self.regime = MarketRegime.SIDEWAYS  # default

    def set_market_regime(self, regime: MarketRegime):
        """Set current market regime for context-aware scoring."""
        self.regime = regime

    def score_fund(self, fund_data: dict) -> dict:
        """
        Score a single fund.
        Args:
            fund_data: dict with fund metrics (return_1y, sharpe_ratio_1y, etc.)
        Returns dict with individual scores and total.
        """
        category = fund_data.get("fund_type", "default")
        weights = self.config.get(category, self.config.get("default", {}))

        # Apply market regime adjustments
        weights = self._adjust_weights_for_regime(weights, category)

        scores = {}

        # Factor 1: Returns (1Y and 3Y)
        scores["return_score"] = self._score_return(
            fund_data.get("return_1y", 0),
            fund_data.get("return_3y", 0),
        )

        # Factor 2: Sharpe Ratio
        scores["sharpe_score"] = self._score_sharpe(
            fund_data.get("sharpe_ratio_1y", 0),
        )

        # Factor 3: Max Drawdown (inverted - lower is better)
        scores["drawdown_score"] = self._score_drawdown(
            abs(fund_data.get("max_drawdown_1y", 0)),
        )

        # Factor 4: Manager Quality
        scores["manager_score"] = self._score_manager(
            fund_data.get("manager_tenure_days", 0),
        )

        # Factor 5: Fee Efficiency
        scores["fee_score"] = self._score_fees(
            fund_data.get("management_fee_pct", 1.5),
        )

        # Factor 6: Size Appropriateness
        scores["size_score"] = self._score_size(
            fund_data.get("aum_yuan", 10),
        )

        # Factor 7: Market Fit
        scores["market_fit_score"] = self._score_market_fit(
            category,
        )

        # Additional factors for index funds
        if category == "指数型":
            scores["tracking_error_score"] = self._score_tracking_error(
                fund_data.get("tracking_error", 0),
            )
            scores["valuation_score"] = self._score_valuation_fit(
                fund_data.get("pe_percentile", 50),
            )

        # Compute weighted total
        total = 0.0
        weight_sum = 0.0
        for factor, weight in weights.items():
            score_key = f"{factor}_score" if not factor.endswith("_score") else factor
            if score_key in scores:
                total += scores[score_key] * weight
                weight_sum += weight

        if weight_sum > 0:
            total /= weight_sum
        else:
            total = 50.0

        scores["total_score"] = round(total, 1)
        scores["fund_code"] = fund_data.get("fund_code", "")

        return scores

    def score_category(self, funds: list[dict],
                       category: str = None) -> list[dict]:
        """
        Score all funds in a category using percentile-based ranking.
        Each factor is scored by percentile within this batch, so the best
        fund in the category gets ~100 on that factor regardless of fund type.
        Returns list of (fund_data, scores) sorted by total_score descending.
        """
        results = []
        for fund in funds:
            if category and fund.get("fund_type") != category:
                continue
            # Get raw absolute scores
            raw_scores = self.score_fund(fund)
            fund["_raw_scores"] = raw_scores
            fund["total_score"] = raw_scores.get("total_score", 0)
            results.append(fund)

        if not results:
            return []

        # --- Percentile-based normalization within category ---
        sample_raw = results[0]["_raw_scores"]
        # Only normalize factors that actually exist
        all_factor_keys = [k for k in sample_raw.keys()
                          if k not in ("fund_code", "total_score")]

        # Detect which factors have meaningful variation
        active_factors = []
        for key in all_factor_keys:
            raw_values = np.array([float(r["_raw_scores"].get(key, 50)) for r in results])
            if raw_values.std() > 1e-6:  # has actual variation
                active_factors.append(key)

        # If no factors have variation, fall back to simple return-based ranking
        if not active_factors:
            for r in results:
                r["scores"] = r["_raw_scores"]
            return sorted(results, key=lambda x: x["total_score"], reverse=True)

        # For each active factor, compute percentile rank within this batch
        from scipy.stats import rankdata
        for key in active_factors:
            raw_values = np.array([float(r["_raw_scores"].get(key, 50)) for r in results])
            ranks = rankdata(raw_values, method="average")
            percentiles = (ranks - 1) / (len(ranks) - 1) * 100 if len(ranks) > 1 else np.full_like(ranks, 50.0)
            for i, r in enumerate(results):
                r["_raw_scores"][key] = round(float(percentiles[i]), 1)

        # Recompute total_score using ONLY active factors
        category_weights = self.config.get(category, self.config.get("default", {}))
        category_weights = self._adjust_weights_for_regime(category_weights, category)

        for r in results:
            raw = r["_raw_scores"]
            total = 0.0
            weight_sum = 0.0
            for factor, weight in category_weights.items():
                score_key = f"{factor}_score" if not factor.endswith("_score") else factor
                if score_key in raw and score_key in active_factors:
                    total += raw[score_key] * weight
                    weight_sum += weight
            if weight_sum > 0:
                total /= weight_sum
            else:
                total = 50.0

            r["scores"] = raw
            r["total_score"] = round(total, 1)

        # Compute overall percentile
        scores_arr = np.array([r["total_score"] for r in results])
        for r in results:
            r["percentile_in_category"] = float(
                (scores_arr < r["total_score"]).mean() * 100
            )

        return sorted(results, key=lambda x: x["total_score"], reverse=True)

    def _adjust_weights_for_regime(self, weights: dict, category: str) -> dict:
        """Adjust factor weights based on current market regime."""
        adjusted = weights.copy()

        if self.regime == MarketRegime.BULL:
            if "return_score" in adjusted:
                adjusted["return_score"] *= 1.2
            if "drawdown_score" in adjusted:
                adjusted["drawdown_score"] *= 0.8
        elif self.regime == MarketRegime.BEAR:
            if "drawdown_score" in adjusted:
                adjusted["drawdown_score"] *= 1.3
            if "return_score" in adjusted:
                adjusted["return_score"] *= 0.8
            if "market_fit_score" in adjusted:
                adjusted["market_fit_score"] *= 1.2

        # Renormalize
        total = sum(adjusted.values())
        if total > 0:
            adjusted = {k: v / total for k, v in adjusted.items()}

        return adjusted

    @staticmethod
    def _score_return(ret_1y: float, ret_3y: float) -> float:
        """Score returns. Excellent: >30% 1Y, Good: >15%, OK: >5%."""
        score = 0.0
        # 1Y return (weighted ~67%)
        if ret_1y > 0.30:
            score += 67
        elif ret_1y > 0.15:
            score += 50
        elif ret_1y > 0.05:
            score += 33
        elif ret_1y > 0:
            score += 15
        elif ret_1y > -0.10:
            score += 5

        # 3Y return (weighted ~33%)
        if ret_3y > 0.80:
            score += 33
        elif ret_3y > 0.40:
            score += 25
        elif ret_3y > 0.10:
            score += 17
        elif ret_3y > 0:
            score += 8

        return score

    @staticmethod
    def _score_sharpe(sharpe: float) -> float:
        """Score Sharpe ratio. >2 = excellent, >1 = good."""
        if sharpe > 2.0:
            return 100
        elif sharpe > 1.5:
            return 85
        elif sharpe > 1.0:
            return 70
        elif sharpe > 0.5:
            return 50
        elif sharpe > 0:
            return 30
        else:
            return 10

    @staticmethod
    def _score_drawdown(max_dd: float) -> float:
        """Score drawdown (inverted). Lower is better. Max dd is positive (e.g., 0.25 = 25%)."""
        if max_dd <= 0.05:
            return 100
        elif max_dd <= 0.10:
            return 85
        elif max_dd <= 0.15:
            return 70
        elif max_dd <= 0.20:
            return 55
        elif max_dd <= 0.30:
            return 35
        elif max_dd <= 0.40:
            return 20
        else:
            return 5

    @staticmethod
    def _score_manager(tenure_days: int) -> float:
        """Score manager stability. >3 years = excellent."""
        if tenure_days > 1095:  # 3 years
            return 100
        elif tenure_days > 730:  # 2 years
            return 80
        elif tenure_days > 365:  # 1 year
            return 60
        elif tenure_days > 180:  # 6 months
            return 30
        elif tenure_days > 0:
            return 10
        else:
            return 0

    @staticmethod
    def _score_fees(fee_pct: float) -> float:
        """Score fee efficiency. Lower is better."""
        if fee_pct <= 0.5:
            return 100
        elif fee_pct <= 0.8:
            return 85
        elif fee_pct <= 1.0:
            return 70
        elif fee_pct <= 1.5:
            return 50
        elif fee_pct <= 2.0:
            return 30
        else:
            return 10

    @staticmethod
    def _score_size(aum_yuan: float) -> float:
        """Score fund size appropriateness (in 亿元). Not too small, not too large."""
        if aum_yuan is None:
            return 50
        if 5 <= aum_yuan <= 50:
            return 100  # Sweet spot
        elif 2 <= aum_yuan <= 100:
            return 80
        elif 1 <= aum_yuan <= 200:
            return 60
        elif aum_yuan > 0:
            return 30
        else:
            return 0

    def _score_market_fit(self, category: str) -> float:
        """Score how well the fund category fits current market regime."""
        if self.regime == MarketRegime.BULL:
            if category in ["股票型", "指数型"]:
                return 100
            elif category == "混合型":
                return 80
            elif category == "债券型":
                return 30
            elif category == "货币型":
                return 10
        elif self.regime == MarketRegime.BEAR:
            if category in ["债券型", "货币型"]:
                return 100
            elif category == "混合型":
                return 50
            elif category in ["股票型", "指数型"]:
                return 15
        else:  # sideways
            if category == "混合型":
                return 90
            elif category == "指数型":
                return 75  # good for DCA
            elif category in ["债券型", "股票型"]:
                return 60
            elif category == "货币型":
                return 40

        return 50

    @staticmethod
    def _score_tracking_error(te: float) -> float:
        """Score tracking error for index funds. Lower is better."""
        if te <= 0.01:
            return 100
        elif te <= 0.02:
            return 80
        elif te <= 0.05:
            return 60
        elif te <= 0.10:
            return 30
        else:
            return 10

    @staticmethod
    def _score_valuation_fit(pe_percentile: float) -> float:
        """Score valuation timing. Lower percentile = cheaper = higher score."""
        if pe_percentile <= 20:
            return 100
        elif pe_percentile <= 35:
            return 80
        elif pe_percentile <= 50:
            return 60
        elif pe_percentile <= 65:
            return 40
        elif pe_percentile <= 80:
            return 20
        else:
            return 5
