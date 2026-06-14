"""Sector rotation and industry trend analysis."""

import pandas as pd
import numpy as np


class SectorRotationAnalyzer:
    """Analyze sector rotation patterns in Chinese A-share market."""

    @staticmethod
    def sector_momentum(sector_df: pd.DataFrame,
                        windows: list = [5, 20, 60]) -> pd.DataFrame:
        """
        Calculate sector momentum across multiple windows.
        Args:
            sector_df: DataFrame with sector performance, must have 'sector_name' and 'return_1d'
        Returns DataFrame with momentum scores.
        """
        if sector_df is None or sector_df.empty:
            return pd.DataFrame()

        result = sector_df.copy()

        for w in windows:
            col = f"momentum_{w}d"
            if "return_1d" in result.columns:
                # Approximate multi-day momentum from daily returns
                result[col] = result["return_1d"].rolling(w, min_periods=1).sum()
            else:
                result[col] = 0

        # Composite momentum score (recent given more weight)
        if all(f"momentum_{w}d" in result.columns for w in windows):
            weights = np.array([0.5, 0.3, 0.2])  # short-term matters more for sectors
            weight_sum = sum(weights[:len(windows)])
            result["momentum_score"] = sum(
                result[f"momentum_{w}d"] * weights[i]
                for i, w in enumerate(windows)
            ) / weight_sum

        return result

    @staticmethod
    def hot_cold_sectors(sector_df: pd.DataFrame,
                         top_n: int = 5) -> dict:
        """
        Identify hottest and coldest sectors.
        Returns {"hot": [...], "cold": [...]}
        """
        if sector_df is None or sector_df.empty:
            return {"hot": [], "cold": []}

        # Determine the column to sort by
        sort_col = None
        for col in ["momentum_score", "return_1d", "return_1w", "return_1m"]:
            if col in sector_df.columns:
                sort_col = col
                break

        if sort_col is None:
            return {"hot": [], "cold": []}

        sorted_df = sector_df.sort_values(sort_col, ascending=False)

        hot = []
        for _, row in sorted_df.head(top_n).iterrows():
            hot.append({
                "sector_name": row.get("sector_name", ""),
                "return": float(row.get(sort_col, 0)),
                "pe": float(row.get("pe_ttm", 0)),
            })

        cold = []
        for _, row in sorted_df.tail(top_n).iterrows():
            cold.append({
                "sector_name": row.get("sector_name", ""),
                "return": float(row.get(sort_col, 0)),
                "pe": float(row.get("pe_ttm", 0)),
            })

        return {"hot": hot, "cold": cold}

    @staticmethod
    def sector_correlation_matrix(sector_returns: dict) -> pd.DataFrame:
        """
        Compute correlation matrix between sectors.
        Args:
            sector_returns: {sector_name: pd.Series of daily returns}
        Returns correlation DataFrame.
        """
        if len(sector_returns) < 2:
            return pd.DataFrame()

        df = pd.DataFrame(sector_returns)
        return df.corr()

    @staticmethod
    def get_sector_etf_recommendations(sector_df: pd.DataFrame,
                                       top_n: int = 3) -> list[str]:
        """
        Recommend sector ETFs based on momentum and valuation.
        """
        # This would ideally cross-reference with actual sector ETF data
        if sector_df is None or sector_df.empty:
            return []

        score_col = None
        for col in ["momentum_score", "return_1m", "return_1w"]:
            if col in sector_df.columns:
                score_col = col
                break

        if score_col is None:
            return []

        # Filter for sectors with reasonable PE
        if "pe_ttm" in sector_df.columns:
            reasonable_pe = sector_df[(sector_df["pe_ttm"] > 0) &
                                      (sector_df["pe_ttm"] < 100)]
            if len(reasonable_pe) > 0:
                sector_df = reasonable_pe

        top = sector_df.nlargest(top_n, score_col)
        return [str(r.get("sector_name", "")) for _, r in top.iterrows()]
