"""Asset allocation optimization using modern portfolio theory."""

import numpy as np
import pandas as pd
from typing import Optional, Tuple
from scipy.optimize import minimize


class AllocationOptimizer:
    """
    Portfolio allocation optimizer.
    Implements Mean-Variance Optimization and Risk Parity.
    """

    def __init__(self, expected_returns: np.ndarray, covariance: np.ndarray):
        """
        Args:
            expected_returns: (n,) array of annualized expected returns
            covariance: (n, n) covariance matrix
        """
        self.er = np.asarray(expected_returns)
        self.cov = np.asarray(covariance)
        self.n = len(self.er)

    def mean_variance(self, target_return: float = None,
                      max_weight: float = 0.4) -> Tuple[np.ndarray, float, float]:
        """
        Mean-Variance optimization.
        If target_return is None, finds minimum variance portfolio.
        Returns (weights, portfolio_return, portfolio_volatility).
        """
        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},  # fully invested
        ]
        bounds = [(0.0, max_weight) for _ in range(self.n)]

        if target_return is not None:
            constraints.append({
                "type": "eq",
                "fun": lambda w: w @ self.er - target_return,
            })

        # Initial guess: equal weights
        w0 = np.ones(self.n) / self.n

        def portfolio_vol(w):
            return np.sqrt(w @ self.cov @ w)

        result = minimize(portfolio_vol, w0, method="SLSQP",
                          bounds=bounds, constraints=constraints,
                          options={"maxiter": 1000, "ftol": 1e-10})

        if not result.success:
            # Fallback to equal weights
            w = w0
        else:
            w = result.x
            w = np.maximum(w, 0)  # enforce non-negative
            w = w / w.sum()       # renormalize

        port_ret = w @ self.er
        port_vol = np.sqrt(w @ self.cov @ w)
        return w, port_ret, port_vol

    def risk_parity(self, max_iter: int = 100,
                    tol: float = 1e-8) -> np.ndarray:
        """
        Risk Parity: equal risk contribution from each asset.
        """
        def risk_contribution(w):
            portfolio_vol = np.sqrt(w @ self.cov @ w)
            if portfolio_vol < 1e-10:
                return np.ones_like(w) / len(w)
            mrc = self.cov @ w / portfolio_vol
            rc = w * mrc
            return rc / portfolio_vol  # normalized

        def objective(w):
            rc = risk_contribution(w)
            target = 1.0 / self.n
            return np.sum((rc - target) ** 2)

        w0 = np.ones(self.n) / self.n
        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
        bounds = [(0.0, 0.5) for _ in range(self.n)]

        result = minimize(objective, w0, method="SLSQP",
                          bounds=bounds, constraints=constraints,
                          options={"maxiter": max_iter, "ftol": tol})

        if result.success:
            w = result.x
            w = np.maximum(w, 0)
            w = w / w.sum()
        else:
            w = w0

        return w

    def efficient_frontier(self, points: int = 50) -> pd.DataFrame:
        """
        Generate the efficient frontier.
        Returns DataFrame with (volatility, return, sharpe, weights).
        """
        min_ret = np.min(self.er)
        max_ret = np.max(self.er)

        # Find minimum variance portfolio
        w_min, r_min, v_min = self.mean_variance(target_return=None)

        # Generate frontier
        target_returns = np.linspace(max(r_min, min_ret * 0.5),
                                     max_ret * 1.1, points)

        frontier = []
        for tr in target_returns:
            try:
                w, r, v = self.mean_variance(target_return=tr)
                sharpe = (r - 0.03) / v if v > 1e-10 else 0
                frontier.append({
                    "volatility": v,
                    "return": r,
                    "sharpe": sharpe,
                    "weights": w.tolist(),
                })
            except Exception:
                continue

        return pd.DataFrame(frontier)

    def tangency_portfolio(self, risk_free_rate: float = 0.03) -> Tuple[np.ndarray, float, float]:
        """
        Find the tangency portfolio (maximum Sharpe ratio).
        """
        def neg_sharpe(w):
            port_ret = w @ self.er
            port_vol = np.sqrt(w @ self.cov @ w)
            if port_vol < 1e-10:
                return 1e10
            return -(port_ret - risk_free_rate) / port_vol

        w0 = np.ones(self.n) / self.n
        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
        bounds = [(0.0, 0.4) for _ in range(self.n)]

        result = minimize(neg_sharpe, w0, method="SLSQP",
                          bounds=bounds, constraints=constraints)

        if result.success:
            w = result.x
            w = np.maximum(w, 0)
            w = w / w.sum()
        else:
            w = w0

        port_ret = w @ self.er
        port_vol = np.sqrt(w @ self.cov @ w)
        return w, port_ret, port_vol

    @staticmethod
    def from_asset_returns(returns_dict: dict[str, np.ndarray],
                           annual_factor: float = 242) -> "AllocationOptimizer":
        """
        Create optimizer from dict of asset return arrays.
        Args:
            returns_dict: {name: daily_returns_array}
        """
        names = list(returns_dict.keys())
        n = len(names)
        if n < 2:
            raise ValueError("Need at least 2 assets")

        # Build return matrix
        min_len = min(len(r) for r in returns_dict.values())
        ret_matrix = np.zeros((min_len, n))
        for i, name in enumerate(names):
            ret_matrix[:, i] = returns_dict[name][:min_len]

        er = np.array([
            float((1 + returns_dict[name]).mean()) ** annual_factor - 1
            for name in names
        ])
        cov = np.cov(ret_matrix.T) * annual_factor

        return AllocationOptimizer(er, cov), names
