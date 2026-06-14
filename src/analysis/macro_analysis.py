"""Macroeconomic environment analysis for investment decisions."""

import pandas as pd
import numpy as np
from typing import Optional


class MacroAnalyzer:
    """Analyze macroeconomic environment and its impact on fund allocation."""

    @staticmethod
    def cpi_assessment(cpi_df: pd.DataFrame, value_col: str = None) -> dict:
        """
        Assess inflation environment from CPI data.
        Returns assessment dict with level and allocation suggestion.
        """
        if cpi_df is None or cpi_df.empty:
            return {"level": "数据不足", "cpi_latest": None, "recommendation": ""}

        # Try to find the CPI value column
        cols = cpi_df.columns.tolist()
        val_col = value_col or next(
            (c for c in cols if any(kw in str(c) for kw in ["CPI", "cpi", "同比", "yoy"])),
            cols[-1] if cols else None
        )
        if val_col is None:
            return {"level": "数据不足", "cpi_latest": None, "recommendation": ""}

        latest = cpi_df.iloc[-1]
        cpi_val = float(latest[val_col]) if hasattr(latest, '__getitem__') else None

        if cpi_val is None:
            return {"level": "数据不足", "cpi_latest": None, "recommendation": ""}

        if cpi_val < 0:
            level = "通缩"
            rec = "通缩环境下债券和货币基金表现较好，权益类需谨慎"
        elif cpi_val < 2:
            level = "温和通胀"
            rec = "适度的通胀对股市有利，可正常配置权益类资产"
        elif cpi_val < 5:
            level = "通胀偏高"
            rec = "高通胀下建议增加商品类、短久期债券和抗通胀资产"
        else:
            level = "高通胀"
            rec = "严重通胀环境下建议增加现金、短债和实物资产"

        return {"level": level, "cpi_latest": cpi_val, "recommendation": rec}

    @staticmethod
    def pmi_assessment(pmi_df: pd.DataFrame, value_col: str = None) -> dict:
        """
        Assess PMI (Purchasing Managers' Index) and its economic implications.
        """
        if pmi_df is None or pmi_df.empty:
            return {"level": "数据不足", "pmi_latest": None, "recommendation": ""}

        cols = pmi_df.columns.tolist()
        val_col = value_col or next(
            (c for c in cols if any(kw in str(c) for kw in ["PMI", "pmi", "制造业"])),
            cols[-1] if cols else None
        )
        if val_col is None:
            return {"level": "数据不足", "pmi_latest": None, "recommendation": ""}

        latest = pmi_df.iloc[-1]
        pmi_val = float(latest[val_col]) if hasattr(latest, '__getitem__') else None

        if pmi_val is None:
            return {"level": "数据不足", "pmi_latest": None, "recommendation": ""}

        if pmi_val > 50:
            level = "经济扩张"
            rec = "PMI>50表明经济处于扩张期，利好股票型和混合型基金"
        elif pmi_val > 48:
            level = "经济平稳"
            rec = "PMI接近50，经济增速放缓但仍稳定，建议均衡配置"
        else:
            level = "经济收缩"
            rec = "PMI<48表明经济收缩，建议增加债券型和货币型基金配置"

        return {"level": level, "pmi_latest": pmi_val, "recommendation": rec}

    @staticmethod
    def interest_rate_assessment(shibor_df: pd.DataFrame) -> dict:
        """
        Assess interest rate environment from SHIBOR.
        """
        if shibor_df is None or shibor_df.empty:
            return {"level": "数据不足", "rate_latest": None, "recommendation": ""}

        try:
            # SHIBOR typically has columns like "ON", "1W", "1M", etc.
            overnight_col = next((c for c in shibor_df.columns
                                  if any(kw in str(c).upper() for kw in ["ON", "O/N", "隔夜"])),
                                 shibor_df.columns[1] if len(shibor_df.columns) > 1 else None)
            if overnight_col is None:
                return {"level": "数据不足", "rate_latest": None, "recommendation": ""}

            latest_rate = float(shibor_df.iloc[-1][overnight_col])

            if latest_rate < 1.5:
                level = "低利率"
                rec = "低利率环境利好股票估值，债券收益率较低，可适当增加权益配置"
            elif latest_rate < 3.0:
                level = "中性利率"
                rec = "利率适中，各类资产均衡配置"
            else:
                level = "高利率"
                rec = "高利率打压股票估值，债券收益率较高，建议增加债券和货币基金"

            return {"level": level, "rate_latest": latest_rate, "recommendation": rec}
        except Exception:
            return {"level": "数据不足", "rate_latest": None, "recommendation": ""}

    @staticmethod
    def composite_macro_score(cpi_dict: dict, pmi_dict: dict,
                              rate_dict: dict) -> dict:
        """
        Generate a composite macro environment score (0-100) and assessment.
        Higher score = more favorable for equity investment.
        """
        score = 50  # neutral start
        factors = []

        # CPI assessment
        cpi_level = cpi_dict.get("level", "")
        if "温和" in cpi_level:
            score += 15
            factors.append("通胀温和(+15)")
        elif "通胀偏高" in cpi_level:
            score -= 10
            factors.append("通胀偏高(-10)")
        elif "通缩" in cpi_level:
            score -= 10
            factors.append("通缩风险(-10)")
        elif "高通胀" in cpi_level:
            score -= 20
            factors.append("高通胀(-20)")

        # PMI assessment
        pmi_level = pmi_dict.get("level", "")
        if "扩张" in pmi_level:
            score += 20
            factors.append("经济扩张(+20)")
        elif "平稳" in pmi_level:
            score += 5
            factors.append("经济平稳(+5)")
        elif "收缩" in pmi_level:
            score -= 15
            factors.append("经济收缩(-15)")

        # Interest rate
        rate_level = rate_dict.get("level", "")
        if "低利率" in rate_level:
            score += 15
            factors.append("低利率(+15)")
        elif "高利率" in rate_level:
            score -= 15
            factors.append("高利率(-15)")

        # Clamp
        score = max(0, min(100, score))

        if score >= 70:
            overall = "宏观环境偏暖，支持权益类资产配置"
        elif score >= 40:
            overall = "宏观环境中性，建议均衡配置"
        else:
            overall = "宏观环境偏冷，建议增加防御性配置"

        return {
            "score": score,
            "overall": overall,
            "factors": factors,
        }
