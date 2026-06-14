"""Technical analysis indicators for market indices and funds."""

import numpy as np
import pandas as pd
from typing import Tuple, Optional


class TechnicalAnalyzer:
    """Compute technical indicators on price series."""

    @staticmethod
    def ma(series: pd.Series, period: int) -> pd.Series:
        """Simple Moving Average."""
        return series.rolling(window=period, min_periods=1).mean()

    @staticmethod
    def ema(series: pd.Series, period: int) -> pd.Series:
        """Exponential Moving Average."""
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def macd(close: pd.Series, fast: int = 12, slow: int = 26,
             signal: int = 9) -> pd.DataFrame:
        """MACD indicator. Returns DataFrame with DIF, DEA, MACD_hist."""
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()
        dif = ema_fast - ema_slow
        dea = dif.ewm(span=signal, adjust=False).mean()
        macd_hist = 2 * (dif - dea)
        return pd.DataFrame({"DIF": dif, "DEA": dea, "MACD": macd_hist})

    @staticmethod
    def rsi(close: pd.Series, period: int = 14) -> pd.Series:
        """Relative Strength Index."""
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    @staticmethod
    def kdj(high: pd.Series, low: pd.Series, close: pd.Series,
            n: int = 9, m1: int = 3, m2: int = 3) -> pd.DataFrame:
        """KDJ indicator. Returns DataFrame with K, D, J."""
        lowest_low = low.rolling(window=n, min_periods=1).min()
        highest_high = high.rolling(window=n, min_periods=1).max()
        rsv = ((close - lowest_low) / (highest_high - lowest_low + 1e-10)) * 100
        k = rsv.ewm(alpha=1 / m1, adjust=False).mean()
        d = k.ewm(alpha=1 / m2, adjust=False).mean()
        j = 3 * k - 2 * d
        return pd.DataFrame({"K": k, "D": d, "J": j})

    @staticmethod
    def bollinger_bands(close: pd.Series, period: int = 20,
                        num_std: float = 2.0) -> pd.DataFrame:
        """Bollinger Bands. Returns DataFrame with upper, middle, lower."""
        middle = close.rolling(window=period, min_periods=1).mean()
        std = close.rolling(window=period, min_periods=1).std()
        upper = middle + num_std * std
        lower = middle - num_std * std
        return pd.DataFrame({"BB_upper": upper, "BB_middle": middle, "BB_lower": lower})

    @staticmethod
    def ma_cross_signal(close: pd.Series) -> pd.Series:
        """
        Golden cross / Death cross detection.
        Returns: 1 (golden cross: MA50 crosses above MA200),
                -1 (death cross: MA50 crosses below MA200),
                 0 (no cross)
        """
        ma50 = close.rolling(50, min_periods=1).mean()
        ma200 = close.rolling(200, min_periods=1).mean()
        diff = ma50 - ma200
        cross = np.where((diff > 0) & (diff.shift(1) <= 0), 1,
                         np.where((diff < 0) & (diff.shift(1) >= 0), -1, 0))
        return pd.Series(cross, index=close.index)

    @staticmethod
    def compute_all_indicators(df: pd.DataFrame, price_col: str = "close") -> pd.DataFrame:
        """
        Compute all technical indicators on a OHLC DataFrame.
        Adds columns: MA5, MA10, MA20, MA60, MA120, MA250,
                      MACD_DIF, MACD_DEA, MACD_hist,
                      RSI_14, K, D, J,
                      BB_upper, BB_middle, BB_lower
        """
        if df is None or df.empty or price_col not in df.columns:
            return df

        close = df[price_col]
        high = df.get("high", close)
        low = df.get("low", close)

        result = df.copy()

        # Moving Averages
        for period in [5, 10, 20, 60, 120, 250]:
            result[f"MA{period}"] = TechnicalAnalyzer.ma(close, period)

        # MACD
        macd_df = TechnicalAnalyzer.macd(close)
        result["MACD_DIF"] = macd_df["DIF"]
        result["MACD_DEA"] = macd_df["DEA"]
        result["MACD_hist"] = macd_df["MACD"]

        # RSI
        result["RSI_14"] = TechnicalAnalyzer.rsi(close, 14)

        # KDJ
        kdj_df = TechnicalAnalyzer.kdj(high, low, close)
        result["K"] = kdj_df["K"]
        result["D"] = kdj_df["D"]
        result["J"] = kdj_df["J"]

        # Bollinger
        bb_df = TechnicalAnalyzer.bollinger_bands(close)
        result["BB_upper"] = bb_df["BB_upper"]
        result["BB_middle"] = bb_df["BB_middle"]
        result["BB_lower"] = bb_df["BB_lower"]

        # Volume ratio (relative to 20-day average)
        if "volume" in df.columns:
            result["vol_ratio"] = df["volume"] / df["volume"].rolling(20, min_periods=1).mean()

        return result

    @staticmethod
    def trend_strength(close: pd.Series, period: int = 60) -> float:
        """
        Calculate trend strength using linear regression slope of MA(period)
        normalized by close price. Returns -1.0 to 1.0.
        """
        if len(close) < period + 20:
            return 0.0

        ma = close.rolling(period, min_periods=1).mean()
        recent_ma = ma.dropna().iloc[-20:]

        if len(recent_ma) < 10:
            return 0.0

        x = np.arange(len(recent_ma))
        slope = np.polyfit(x, recent_ma.values, 1)[0]

        # Normalize by average price
        avg_price = recent_ma.mean()
        if avg_price == 0:
            return 0.0

        normalized = slope / avg_price * 100
        return max(-1.0, min(1.0, normalized))  # clamped to [-1, 1]

    @staticmethod
    def detect_divergence(close: pd.Series, indicator: pd.Series,
                          window: int = 60) -> Tuple[bool, str]:
        """
        Detect divergence between price and an indicator (e.g., RSI, MACD).
        Returns (has_divergence, type) where type is 'bullish' or 'bearish'.
        """
        if len(close) < window:
            return False, ""

        recent_close = close.iloc[-window:]
        recent_ind = indicator.iloc[-window:]

        # Find local extremes
        close_high_idx = recent_close.idxmax()
        ind_high_idx = recent_ind.idxmax()
        close_low_idx = recent_close.idxmin()
        ind_low_idx = recent_ind.idxmin()

        # Bearish divergence: price higher high, indicator lower high
        if close_high_idx > ind_high_idx:
            return True, "bearish"

        # Bullish divergence: price lower low, indicator higher low
        if close_low_idx > ind_low_idx:
            return True, "bullish"

        return False, ""
