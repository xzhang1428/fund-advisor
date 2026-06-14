"""P&L computation and return attribution for portfolios."""

import numpy as np
import pandas as pd
from typing import Optional
from datetime import date


class PnLCalculator:
    """Calculate portfolio-level P&L and performance metrics."""

    @staticmethod
    def compute_daily_pnl(holdings: list, nav_data: dict) -> pd.DataFrame:
        """
        Compute daily P&L from holdings and NAV history.
        Args:
            holdings: list of Holding objects
            nav_data: {fund_code: pd.DataFrame with date and nav columns}
        Returns DataFrame with daily portfolio values.
        """
        if not holdings or not nav_data:
            return pd.DataFrame()

        # Build combined portfolio NAV series
        daily_values = {}

        for h in holdings:
            if h.fund_code not in nav_data:
                continue
            nav_df = nav_data[h.fund_code]
            if nav_df is None or nav_df.empty:
                continue

            for _, row in nav_df.iterrows():
                d = row["date"] if "date" in row else row.name
                val = h.shares * row["nav"]
                daily_values[d] = daily_values.get(d, 0) + val

        if not daily_values:
            return pd.DataFrame()

        df = pd.DataFrame(
            sorted(daily_values.items()),
            columns=["date", "portfolio_value"]
        )
        df["daily_return"] = df["portfolio_value"].pct_change()
        df["cumulative_return"] = (1 + df["daily_return"].fillna(0)).cumprod() - 1
        return df

    @staticmethod
    def compute_returns(portfolio_values: pd.Series) -> dict:
        """Compute return metrics from portfolio value series."""
        if len(portfolio_values) < 2:
            return {}

        daily_ret = portfolio_values.pct_change().dropna()
        if len(daily_ret) == 0:
            return {}

        from src.analysis.fund_performance import PerformanceCalculator
        pc = PerformanceCalculator

        return {
            "total_return": pc.cumulative_return(daily_ret),
            "annualized_return": pc.annualized_return(daily_ret),
            "annualized_volatility": pc.annualized_volatility(daily_ret),
            "sharpe_ratio": pc.sharpe_ratio(daily_ret),
            "max_drawdown": pc.max_drawdown(portfolio_values)[0],
            "calmar_ratio": pc.calmar_ratio(daily_ret, portfolio_values),
        }

    @staticmethod
    def return_attribution(holdings: list,
                           holding_returns: dict[str, float],
                           holding_weights: dict[str, float]) -> pd.DataFrame:
        """
        Attribute portfolio return to individual holdings.
        Args:
            holdings: list of holding dicts
            holding_returns: {fund_code: return_pct}
            holding_weights: {fund_code: weight}
        Returns DataFrame with contribution breakdown.
        """
        rows = []
        for h in holdings:
            code = h.get("fund_code", h.fund_code if hasattr(h, "fund_code") else "")
            ret = holding_returns.get(code, 0)
            weight = holding_weights.get(code, 0)
            contribution = ret * weight
            rows.append({
                "fund_code": code,
                "fund_name": h.get("fund_name", ""),
                "weight": weight,
                "return": ret,
                "contribution": contribution,
            })

        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.sort_values("contribution", ascending=False)
        return df
