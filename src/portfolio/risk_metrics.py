"""Portfolio-level risk metrics computation."""

import numpy as np
import pandas as pd
from typing import Optional


class PortfolioRiskMetrics:
    """Compute portfolio risk metrics."""

    @staticmethod
    def value_at_risk(daily_returns: pd.Series,
                      confidence: float = 0.95) -> float:
        """
        Value at Risk (VaR) using historical method.
        Returns the maximum expected loss at given confidence level.
        """
        if len(daily_returns) < 50:
            return 0.0
        return float(np.percentile(daily_returns.dropna(), (1 - confidence) * 100))

    @staticmethod
    def conditional_var(daily_returns: pd.Series,
                        confidence: float = 0.95) -> float:
        """
        Conditional VaR (CVaR / Expected Shortfall).
        Average loss beyond VaR.
        """
        if len(daily_returns) < 50:
            return 0.0
        var = PortfolioRiskMetrics.value_at_risk(daily_returns, confidence)
        losses = daily_returns[daily_returns <= var]
        if len(losses) == 0:
            return var
        return float(losses.mean())

    @staticmethod
    def max_drawdown_period(nav_series: pd.Series) -> dict:
        """Detailed max drawdown analysis including recovery time."""
        if len(nav_series) < 2:
            return {}

        cummax = nav_series.expanding().max()
        drawdown = (nav_series - cummax) / cummax

        max_dd_idx = drawdown.idxmin()
        max_dd_val = float(drawdown.min())

        # Find peak before trough
        before_trough = nav_series[:max_dd_idx]
        if len(before_trough) == 0:
            return {"max_drawdown": max_dd_val}

        peak_idx = before_trough.idxmax()
        peak_val = float(before_trough.max())

        # Find recovery point (when NAV exceeds previous peak)
        after_trough = nav_series[max_dd_idx:]
        recovery_idx = None
        for idx, val in after_trough.items():
            if val >= peak_val:
                recovery_idx = idx
                break

        recovery_days = None
        if recovery_idx is not None and hasattr(nav_series, 'index'):
            try:
                recovery_days = (nav_series.index.get_loc(recovery_idx) -
                                 nav_series.index.get_loc(max_dd_idx))
            except Exception:
                pass

        return {
            "max_drawdown": max_dd_val,
            "peak_value": peak_val,
            "trough_value": float(nav_series[max_dd_idx]),
            "peak_date": str(peak_idx),
            "trough_date": str(max_dd_idx),
            "recovery_date": str(recovery_idx) if recovery_idx else "未恢复",
            "recovery_days": recovery_days,
        }

    @staticmethod
    def risk_budget(volatilities: np.ndarray,
                    corr_matrix: np.ndarray,
                    weights: np.ndarray) -> np.ndarray:
        """
        Compute risk contribution of each asset.
        Returns risk contribution per asset (sum = total portfolio vol).
        """
        cov = np.diag(volatilities) @ corr_matrix @ np.diag(volatilities)
        portfolio_vol = np.sqrt(weights.T @ cov @ weights)
        if portfolio_vol < 1e-10:
            return np.zeros_like(weights)

        # Marginal risk contribution
        mrc = cov @ weights / portfolio_vol
        rc = weights * mrc  # component risk contribution
        return rc

    @staticmethod
    def diversification_score(weights: np.ndarray,
                              cov_matrix: np.ndarray) -> float:
        """
        Diversification score (0-100).
        Higher = more diversified.
        """
        n = len(weights)
        if n < 2:
            return 50.0

        portfolio_var = weights.T @ cov_matrix @ weights
        if portfolio_var < 1e-10:
            return 100.0

        # Equal weight as benchmark
        ew = np.ones(n) / n
        ew_var = ew.T @ cov_matrix @ ew

        if ew_var < 1e-10:
            return 100.0

        # Compare to equally-weighted portfolio
        ratio = portfolio_var / ew_var
        score = 100 * min(1.0, 1.0 / max(ratio, 0.1))
        return float(score)
