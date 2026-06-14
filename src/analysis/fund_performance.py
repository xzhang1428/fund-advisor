"""Fund performance metrics computation."""

import numpy as np
import pandas as pd
from typing import Tuple, Optional


class PerformanceCalculator:
    """Calculate fund performance metrics from NAV history."""

    @staticmethod
    def daily_returns(nav_series: pd.Series) -> pd.Series:
        """Calculate daily returns from NAV series."""
        return nav_series.pct_change().dropna()

    @staticmethod
    def annualized_return(daily_returns: pd.Series,
                          trading_days: int = 242) -> float:
        """Annualized return from daily returns."""
        if len(daily_returns) == 0:
            return 0.0
        total_return = (1 + daily_returns).prod()
        years = len(daily_returns) / trading_days
        if years <= 0:
            return 0.0
        return float(total_return ** (1 / years) - 1)

    @staticmethod
    def cumulative_return(daily_returns: pd.Series) -> float:
        """Total cumulative return."""
        if len(daily_returns) == 0:
            return 0.0
        return float((1 + daily_returns).prod() - 1)

    @staticmethod
    def annualized_volatility(daily_returns: pd.Series,
                              trading_days: int = 242) -> float:
        """Annualized volatility (standard deviation)."""
        if len(daily_returns) < 2:
            return 0.0
        return float(daily_returns.std() * np.sqrt(trading_days))

    @staticmethod
    def sharpe_ratio(daily_returns: pd.Series,
                     risk_free_rate: float = 0.03,
                     trading_days: int = 242) -> float:
        """Sharpe Ratio: (annualized_return - risk_free_rate) / annualized_volatility."""
        ann_ret = PerformanceCalculator.annualized_return(daily_returns, trading_days)
        ann_vol = PerformanceCalculator.annualized_volatility(daily_returns, trading_days)
        if ann_vol == 0:
            return 0.0
        return float((ann_ret - risk_free_rate) / ann_vol)

    @staticmethod
    def max_drawdown(nav_series: pd.Series) -> Tuple[float, Optional[str], Optional[str]]:
        """
        Maximum drawdown from NAV series.
        Returns (max_drawdown_pct, start_date, end_date).
        """
        if len(nav_series) < 2:
            return 0.0, None, None

        cumulative_max = nav_series.expanding().max()
        drawdown = (nav_series - cumulative_max) / cumulative_max

        max_dd = float(drawdown.min())
        max_dd_end = drawdown.idxmin() if hasattr(drawdown, 'idxmin') else None
        if max_dd_end is not None:
            peak_series = nav_series[:max_dd_end]
            if len(peak_series) > 0:
                max_dd_start = peak_series.idxmax()
            else:
                max_dd_start = None
        else:
            max_dd_start = None

        return max_dd, str(max_dd_start) if max_dd_start else None, str(max_dd_end) if max_dd_end else None

    @staticmethod
    def calmar_ratio(daily_returns: pd.Series, nav_series: pd.Series,
                     trading_days: int = 242) -> float:
        """Calmar Ratio: annualized_return / |max_drawdown|."""
        ann_ret = PerformanceCalculator.annualized_return(daily_returns, trading_days)
        max_dd, _, _ = PerformanceCalculator.max_drawdown(nav_series)
        if abs(max_dd) < 1e-10:
            return 0.0
        return float(ann_ret / abs(max_dd))

    @staticmethod
    def sortino_ratio(daily_returns: pd.Series,
                      risk_free_rate: float = 0.03,
                      trading_days: int = 242) -> float:
        """Sortino Ratio: uses downside deviation instead of total volatility."""
        ann_ret = PerformanceCalculator.annualized_return(daily_returns, trading_days)
        downside = daily_returns[daily_returns < 0]
        if len(downside) < 2:
            return 0.0
        downside_std = downside.std() * np.sqrt(trading_days)
        if downside_std == 0:
            return 0.0
        return float((ann_ret - risk_free_rate) / downside_std)

    @staticmethod
    def information_ratio(fund_returns: pd.Series,
                          benchmark_returns: pd.Series,
                          trading_days: int = 242) -> float:
        """Information Ratio: excess return over benchmark / tracking error."""
        if len(fund_returns) < 2 or len(benchmark_returns) < 2:
            return 0.0
        # Align indices
        common_index = fund_returns.index.intersection(benchmark_returns.index)
        if len(common_index) < 2:
            return 0.0
        excess = fund_returns[common_index] - benchmark_returns[common_index]
        tracking_error = excess.std() * np.sqrt(trading_days)
        if tracking_error == 0:
            return 0.0
        ann_excess = PerformanceCalculator.annualized_return(excess, trading_days)
        return float(ann_excess / tracking_error)

    @staticmethod
    def tracking_error(fund_returns: pd.Series,
                       benchmark_returns: pd.Series,
                       trading_days: int = 242) -> float:
        """Tracking error: std of excess returns annualized."""
        common = fund_returns.index.intersection(benchmark_returns.index)
        if len(common) < 2:
            return 0.0
        excess = fund_returns[common] - benchmark_returns[common]
        return float(excess.std() * np.sqrt(trading_days))

    @staticmethod
    def alpha_beta(fund_returns: pd.Series,
                   benchmark_returns: pd.Series,
                   trading_days: int = 242) -> Tuple[float, float]:
        """Calculate alpha and beta relative to a benchmark."""
        common = fund_returns.index.intersection(benchmark_returns.index)
        if len(common) < 10:
            return 0.0, 0.0

        f = fund_returns[common].values
        b = benchmark_returns[common].values

        # Beta = Cov(fund, benchmark) / Var(benchmark)
        cov = np.cov(f, b)[0, 1]
        var = np.var(b)
        beta = cov / var if var != 0 else 0.0

        # Alpha = annualized fund return - beta * annualized benchmark return
        ann_fund = PerformanceCalculator.annualized_return(
            fund_returns[common], trading_days)
        ann_bench = PerformanceCalculator.annualized_return(
            benchmark_returns[common], trading_days)
        alpha = ann_fund - beta * ann_bench

        return float(alpha), float(beta)

    @staticmethod
    def compute_all_metrics(nav_df: pd.DataFrame,
                            nav_col: str = "nav",
                            benchmark_nav: pd.Series = None,
                            risk_free_rate: float = 0.03) -> dict:
        """
        Compute all performance metrics from NAV DataFrame.
        Expects nav_df to have a 'date' column and a nav column.
        Returns a dict of metrics.
        """
        if nav_df is None or nav_df.empty:
            return {}

        # Sort by date and extract NAV series
        df = nav_df.sort_values("date") if "date" in nav_df.columns else nav_df
        nav_series = df[nav_col].dropna()

        if len(nav_series) < 20:
            return {}

        daily_ret = PerformanceCalculator.daily_returns(nav_series)

        metrics = {}
        # Standard period returns
        for label, days in [("return_1w", 5), ("return_1m", 21),
                             ("return_3m", 63), ("return_6m", 126),
                             ("return_1y", 242), ("return_3y", 726)]:
            if len(daily_ret) >= days:
                metrics[label] = PerformanceCalculator.cumulative_return(daily_ret.iloc[-days:])
            else:
                metrics[label] = PerformanceCalculator.cumulative_return(daily_ret)

        # YTD return
        if "date" in df.columns:
            current_year = pd.Timestamp.now().year
            ytd_ret = daily_ret[daily_ret.index.get_level_values(0) if isinstance(
                daily_ret.index, pd.MultiIndex) else slice(None)]
            metrics["return_ytd"] = metrics.get("return_1y", 0)

        # Annualized metrics
        metrics["annualized_return_3y"] = PerformanceCalculator.annualized_return(daily_ret)
        metrics["sharpe_ratio_1y"] = PerformanceCalculator.sharpe_ratio(
            daily_ret.iloc[-242:] if len(daily_ret) > 242 else daily_ret, risk_free_rate)
        metrics["sharpe_ratio_3y"] = PerformanceCalculator.sharpe_ratio(daily_ret, risk_free_rate)

        # Drawdown
        max_dd, dd_start, dd_end = PerformanceCalculator.max_drawdown(nav_series)
        metrics["max_drawdown_1y"] = PerformanceCalculator.max_drawdown(
            nav_series.iloc[-242:] if len(nav_series) > 242 else nav_series)[0]
        metrics["max_drawdown_3y"] = max_dd

        # Volatility
        metrics["volatility_1y"] = PerformanceCalculator.annualized_volatility(
            daily_ret.iloc[-242:] if len(daily_ret) > 242 else daily_ret)
        metrics["volatility_3y"] = PerformanceCalculator.annualized_volatility(daily_ret)

        # Calmar
        metrics["calmar_ratio"] = PerformanceCalculator.calmar_ratio(daily_ret, nav_series)

        # Alpha/Beta vs benchmark
        if benchmark_nav is not None and len(benchmark_nav) > 10:
            bench_ret = PerformanceCalculator.daily_returns(benchmark_nav)
            alpha, beta = PerformanceCalculator.alpha_beta(daily_ret, bench_ret)
            metrics["alpha"] = alpha
            metrics["beta"] = beta
            metrics["information_ratio"] = PerformanceCalculator.information_ratio(daily_ret, bench_ret)
            metrics["tracking_error"] = PerformanceCalculator.tracking_error(daily_ret, bench_ret)
        else:
            metrics["alpha"] = 0.0
            metrics["beta"] = 1.0
            metrics["information_ratio"] = 0.0
            metrics["tracking_error"] = 0.0

        return metrics
