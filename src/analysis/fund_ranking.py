"""Fund ranking and comparison within categories."""

import numpy as np
import pandas as pd
from typing import Optional


class FundRanking:
    """Rank funds within their categories."""

    @staticmethod
    def rank_by_metric(funds_df: pd.DataFrame, metric_col: str,
                       ascending: bool = False) -> pd.DataFrame:
        """
        Rank funds by a single metric.
        Higher is better unless ascending=True.
        """
        if metric_col not in funds_df.columns:
            return funds_df
        result = funds_df.copy()
        result["rank"] = result[metric_col].rank(ascending=ascending, method="min")
        result["percentile"] = result[metric_col].rank(ascending=ascending, pct=True) * 100
        return result.sort_values("rank")

    @staticmethod
    def composite_rank(funds_df: pd.DataFrame,
                       metrics: dict[str, bool],
                       weights: Optional[dict[str, float]] = None) -> pd.DataFrame:
        """
        Rank funds by composite score across multiple metrics.
        Args:
            metrics: {metric_col: ascending?} e.g., {"return_1y": False, "max_drawdown": True}
            weights: {metric_col: weight} weights for each metric
        """
        result = funds_df.copy()
        if weights is None:
            weights = {m: 1.0 for m in metrics}

        total_weight = sum(weights.values())
        score = pd.Series(0.0, index=result.index)

        for col, ascending in metrics.items():
            if col not in result.columns:
                continue
            # Normalize to 0-100
            ranked = result[col].rank(ascending=ascending, pct=True)
            w = weights.get(col, 1.0) / total_weight
            score += ranked * w

        result["composite_score"] = score * 100
        result["rank"] = result["composite_score"].rank(ascending=False, method="min")
        return result.sort_values("rank")

    @staticmethod
    def category_ranking(funds_df: pd.DataFrame,
                         category_col: str = "fund_type") -> dict[str, pd.DataFrame]:
        """Rank funds within each category."""
        rankings = {}
        for category, group in funds_df.groupby(category_col):
            if len(group) < 3:
                continue
            metrics = {
                "return_1y": False,
                "sharpe_ratio_1y": False,
                "max_drawdown_1y": True,
                "volatility_1y": True,
            }
            available = [m for m in metrics if m in group.columns]
            if len(available) < 2:
                continue
            rankings[category] = FundRanking.composite_rank(
                group, {m: metrics[m] for m in available}
            )
        return rankings

    @staticmethod
    def top_funds(funds_df: pd.DataFrame, n: int = 10,
                  category: str = None) -> pd.DataFrame:
        """Get top N funds, optionally filtered by category."""
        df = funds_df.copy()
        if category and "fund_type" in df.columns:
            df = df[df["fund_type"] == category]
        if "composite_score" not in df.columns:
            metrics = {
                "return_1y": False,
                "sharpe_ratio_1y": False,
                "max_drawdown_1y": True,
            }
            available = {m: v for m, v in metrics.items() if m in df.columns}
            if available:
                df = FundRanking.composite_rank(df, available)
        if "rank" in df.columns:
            return df.nsmallest(n, "rank")
        return df.head(n)
