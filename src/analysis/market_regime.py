"""Market regime detection (牛市/熊市/震荡)."""

import numpy as np
import pandas as pd
from typing import Tuple
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import MarketRegime
from src.analysis.technical import TechnicalAnalyzer


class MarketRegimeDetector:
    """Detect current market regime using multiple signals."""

    @staticmethod
    def detect_regime(index_df: pd.DataFrame,
                      price_col: str = "close") -> Tuple[MarketRegime, float]:
        """
        Detect market regime from index price history.
        Args:
            index_df: DataFrame with OHLC data (at least 250 rows)
        Returns (regime, confidence 0-1)
        """
        if index_df is None or index_df.empty or len(index_df) < 60:
            return MarketRegime.SIDEWAYS, 0.3

        close = index_df[price_col].dropna()
        if len(close) < 60:
            return MarketRegime.SIDEWAYS, 0.3

        # Compute key MAs
        ma60 = close.rolling(60, min_periods=1).mean().iloc[-1]
        ma120 = close.rolling(120, min_periods=1).mean().iloc[-1] if len(close) >= 120 else ma60
        ma250 = close.rolling(250, min_periods=1).mean().iloc[-1] if len(close) >= 250 else ma60

        current_price = close.iloc[-1]

        # MA slope (trend direction of MA60 over last 20 days)
        if len(close) >= 80:
            ma60_series = close.rolling(60, min_periods=1).mean()
            recent_ma60 = ma60_series.dropna().iloc[-20:]
            if len(recent_ma60) >= 10:
                x = np.arange(len(recent_ma60))
                slope = np.polyfit(x, recent_ma60.values, 1)[0]
                ma_slope_normalized = slope / recent_ma60.mean()
            else:
                ma_slope_normalized = 0
        else:
            ma_slope_normalized = 0

        # Volume trend
        if "volume" in index_df.columns and len(index_df) >= 120:
            vol = index_df["volume"].dropna()
            vol_30 = vol.iloc[-30:].mean() if len(vol) >= 30 else vol.mean()
            vol_90 = vol.iloc[-90:].mean() if len(vol) >= 90 else vol.mean()
            vol_trend = vol_30 / vol_90 if vol_90 > 0 else 1.0
        else:
            vol_trend = 1.0

        # Classification
        signals = []
        weights = []

        # Signal 1: Price vs MA250 (年线)
        if len(close) >= 250:
            price_vs_ma250 = current_price / ma250 - 1
            if price_vs_ma250 > 0.03:
                signals.append(1)    # bullish
            elif price_vs_ma250 < -0.03:
                signals.append(-1)   # bearish
            else:
                signals.append(0)    # neutral
            weights.append(0.30)
        else:
            weights.append(0)

        # Signal 2: MA alignment (MA60 vs MA120)
        if len(close) >= 120:
            if ma60 > ma120:
                signals.append(1)
            else:
                signals.append(-1)
            weights.append(0.25)
        else:
            weights.append(0)

        # Signal 3: MA60 slope
        if ma_slope_normalized > 0.001:
            signals.append(1)
        elif ma_slope_normalized < -0.001:
            signals.append(-1)
        else:
            signals.append(0)
        weights.append(0.25)

        # Signal 4: Volume trend
        if vol_trend > 1.1:
            signals.append(1)
        elif vol_trend < 0.9:
            signals.append(-1)
        else:
            signals.append(0)
        weights.append(0.20)

        # Weighted signal
        if sum(weights) == 0:
            return MarketRegime.SIDEWAYS, 0.3

        weighted_signal = sum(s * w for s, w in zip(signals, weights)) / sum(weights)

        # Confidence
        confidence = min(abs(weighted_signal) * 1.5, 1.0)

        if weighted_signal > 0.3:
            return MarketRegime.BULL, confidence
        elif weighted_signal < -0.3:
            return MarketRegime.BEAR, confidence
        else:
            return MarketRegime.SIDEWAYS, 1.0 - confidence

    @staticmethod
    def get_regime_summary(regime: MarketRegime, confidence: float) -> str:
        """Generate a human-readable regime summary."""
        confidence_pct = confidence * 100
        if regime == MarketRegime.BULL:
            return f"牛市 (置信度: {confidence_pct:.0f}%) - 市场处于上升趋势，可适当增加权益类资产配置"
        elif regime == MarketRegime.BEAR:
            return f"熊市 (置信度: {confidence_pct:.0f}%) - 市场处于下降趋势，建议增加防御性资产配置"
        else:
            return f"震荡市 (置信度: {confidence_pct:.0f}%) - 市场方向不明，适合定投策略和逢低布局"

    @staticmethod
    def favored_categories(regime: MarketRegime) -> list[str]:
        """Return fund categories favored in current regime."""
        if regime == MarketRegime.BULL:
            return ["股票型", "指数型", "混合型"]
        elif regime == MarketRegime.BEAR:
            return ["债券型", "货币型"]
        else:
            return ["混合型", "债券型", "指数型"]  # 适合定投

    @staticmethod
    def get_regime_allocation_adj(regime: MarketRegime) -> dict:
        """
        Get allocation adjustment suggestions based on market regime.
        Returns adjustment multipliers for each category.
        """
        if regime == MarketRegime.BULL:
            return {"股票型": 1.2, "指数型": 1.2, "混合型": 1.1,
                    "债券型": 0.8, "货币型": 0.7, "QDII": 1.0}
        elif regime == MarketRegime.BEAR:
            return {"股票型": 0.7, "指数型": 0.7, "混合型": 0.8,
                    "债券型": 1.3, "货币型": 1.4, "QDII": 1.0}
        else:
            return {"股票型": 1.0, "指数型": 1.0, "混合型": 1.1,
                    "债券型": 1.1, "货币型": 1.0, "QDII": 1.0}
