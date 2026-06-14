"""PE/PB valuation analysis for market timing."""

import numpy as np
import pandas as pd
from typing import Optional


class ValuationAnalyzer:
    """Analyze index/market valuation using PE/PB percentile."""

    @staticmethod
    def pe_percentile(current_pe: float, historical_pe: pd.Series) -> float:
        """
        Calculate current PE's percentile within history.
        Returns 0-100, where 0 = cheapest, 100 = most expensive.
        """
        if historical_pe.empty or current_pe is None or np.isnan(current_pe):
            return 50.0  # neutral if no data

        clean = historical_pe.dropna()
        if len(clean) < 50:
            return 50.0

        # Percentile: what fraction of historical PE values are BELOW current
        percentile = (clean < current_pe).mean() * 100
        return float(percentile)

    @staticmethod
    def valuation_zone(pe_percentile: float) -> str:
        """
        Classify valuation zone based on PE percentile.
        Returns zone name in Chinese.
        """
        if pe_percentile <= 20:
            return "极度低估"
        elif pe_percentile <= 35:
            return "低估"
        elif pe_percentile <= 65:
            return "估值合理"
        elif pe_percentile <= 80:
            return "高估"
        else:
            return "极度高估"

    @staticmethod
    def valuation_signal(pe_percentile: float) -> str:
        """
        Generate investment signal based on valuation percentile.
        """
        if pe_percentile <= 20:
            return "买入"      # extremely undervalued → strong buy
        elif pe_percentile <= 35:
            return "加仓"      # undervalued → accumulate
        elif pe_percentile <= 65:
            return "持有"      # fair → hold
        elif pe_percentile <= 80:
            return "减仓"      # overvalued → reduce
        else:
            return "卖出"      # extremely overvalued → sell

    @staticmethod
    def compute_pe_pb_percentiles(historical_df: pd.DataFrame,
                                  current_pe: float,
                                  current_pb: float = None,
                                  pe_col: str = "pe_ttm",
                                  pb_col: str = "pb") -> dict:
        """
        Compute PE/PB percentiles from historical data.
        Args:
            historical_df: DataFrame with PE/PB history
            current_pe: Current PE value
            current_pb: Current PB value (optional)
        Returns dict with percentiles, zones, signals.
        """
        result = {
            "pe_percentile": 50.0,
            "pe_zone": "数据不足",
            "pe_signal": "持有",
            "pb_percentile": None,
            "pb_zone": None,
            "pb_signal": None,
        }

        if pe_col in historical_df.columns:
            hist_pe = historical_df[pe_col]
            result["pe_percentile"] = ValuationAnalyzer.pe_percentile(current_pe, hist_pe)
            result["pe_zone"] = ValuationAnalyzer.valuation_zone(result["pe_percentile"])
            result["pe_signal"] = ValuationAnalyzer.valuation_signal(result["pe_percentile"])

        if pb_col in historical_df.columns and current_pb is not None:
            hist_pb = historical_df[pb_col]
            result["pb_percentile"] = ValuationAnalyzer.pe_percentile(current_pb, hist_pb)
            result["pb_zone"] = ValuationAnalyzer.valuation_zone(result["pb_percentile"])
            result["pb_signal"] = ValuationAnalyzer.valuation_signal(result["pb_percentile"])

        return result

    @staticmethod
    def composite_valuation_score(pe_percentile: float,
                                  pb_percentile: Optional[float] = None) -> float:
        """
        Composite valuation score 0-100.
        Higher = more undervalued (better buying opportunity).
        """
        scores = [100 - pe_percentile]
        if pb_percentile is not None:
            scores.append(100 - pb_percentile)
        avg = np.mean(scores)
        return float(avg)

    @staticmethod
    def historical_percentile_chart(historical_pe: pd.Series,
                                    current_pe: float) -> dict:
        """Generate data for a valuation gauge/chart."""
        if historical_pe.empty:
            return {}

        clean = historical_pe.dropna()
        if len(clean) < 20:
            return {}

        return {
            "current_pe": current_pe,
            "min_pe": float(clean.min()),
            "max_pe": float(clean.max()),
            "median_pe": float(clean.median()),
            "mean_pe": float(clean.mean()),
            "p25_pe": float(clean.quantile(0.25)),
            "p75_pe": float(clean.quantile(0.75)),
            "percentile": ValuationAnalyzer.pe_percentile(current_pe, clean),
            "zone": ValuationAnalyzer.valuation_zone(
                ValuationAnalyzer.pe_percentile(current_pe, clean)),
        }
