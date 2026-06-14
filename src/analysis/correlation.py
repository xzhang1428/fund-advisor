"""Correlation analysis between funds and indices."""

import pandas as pd
import numpy as np


class CorrelationAnalyzer:
    """Analyze correlations between assets for portfolio construction."""

    @staticmethod
    def correlation_matrix(returns_dict: dict[str, pd.Series]) -> pd.DataFrame:
        """
        Compute correlation matrix from multiple return series.
        Args:
            returns_dict: {name: daily_returns_series}
        Returns DataFrame of correlations.
        """
        if len(returns_dict) < 2:
            return pd.DataFrame()

        df = pd.DataFrame(returns_dict)
        return df.corr()

    @staticmethod
    def covariance_matrix(returns_dict: dict[str, pd.Series]) -> pd.DataFrame:
        """Compute covariance matrix for portfolio optimization."""
        df = pd.DataFrame(returns_dict)
        return df.cov() * 242  # annualized

    @staticmethod
    def expected_returns(returns_dict: dict[str, pd.Series]) -> pd.Series:
        """Compute expected annualized returns from historical data."""
        result = {}
        for name, returns in returns_dict.items():
            if len(returns) > 0:
                result[name] = float(((1 + returns).prod()) ** (242 / len(returns)) - 1)
            else:
                result[name] = 0.0
        return pd.Series(result)

    @staticmethod
    def diversification_ratio(weights: np.ndarray,
                              volatilities: np.ndarray,
                              portfolio_volatility: float) -> float:
        """
        Diversification ratio: weighted avg volatility / portfolio volatility.
        Higher = better diversification benefit.
        """
        weighted_vol = np.sum(weights * volatilities)
        if portfolio_volatility < 1e-10:
            return 0.0
        return float(weighted_vol / portfolio_volatility)

    @staticmethod
    def minimum_correlation_portfolio(corr_matrix: pd.DataFrame) -> np.ndarray:
        """
        Heuristic: allocate inversely to average correlation.
        Assets with lower average correlation get higher weight.
        """
        n = len(corr_matrix)
        if n == 0:
            return np.array([])

        avg_corr = corr_matrix.mean()
        # Invert correlation (lower correlation → higher weight)
        inv_corr = 1.0 / (avg_corr.clip(lower=0.1))
        weights = inv_corr / inv_corr.sum()
        return weights.values
