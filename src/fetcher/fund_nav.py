"""Fetch fund NAV and basic info data from akshare."""

import pandas as pd
import sys
from pathlib import Path
from datetime import date, datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.fetcher.base import BaseFetcher, with_cache, with_retry
from config.settings import FUND_TYPE_MAPPING


class FundFetcher(BaseFetcher):
    """Fetch Chinese fund data (NAV, basic info, rankings)."""

    @with_cache
    @with_retry
    def fetch_all_fund_list(self) -> pd.DataFrame:
        """
        Fetch all available funds with basic info.
        Returns DataFrame with fund codes, names, types, etc.
        """
        import akshare as ak
        self._rate_limit()

        try:
            # Get open-end fund list
            df = ak.fund_open_fund_daily_em()
            print(f"  Fetched {len(df)} funds from open fund list")
            return df
        except Exception as e:
            print(f"  [Error] fetch_all_fund_list: {e}")
            return pd.DataFrame()

    @with_cache
    @with_retry
    def fetch_fund_nav(self, fund_code: str, start_date: str = None,
                       end_date: str = None) -> pd.DataFrame:
        """
        Fetch NAV history for a single fund.
        Args:
            fund_code: 6-digit fund code
        Returns DataFrame with NAV history
        """
        import akshare as ak

        if end_date is None:
            end_date = date.today().strftime("%Y%m%d")
        if start_date is None:
            start_date = (date.today() - timedelta(days=365 * 5)).strftime("%Y%m%d")

        self._rate_limit()

        try:
            df = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
            if df is None or df.empty:
                # Try alternative endpoint
                df = ak.fund_nav_open_fund_daily_em(symbol=fund_code)
            if df is None or df.empty:
                return pd.DataFrame()
        except Exception:
            try:
                df = ak.fund_nav_open_fund_daily_em(symbol=fund_code)
            except Exception:
                return pd.DataFrame()

        if df is None or df.empty:
            return pd.DataFrame()

        # Normalize columns
        col_map = {
            "净值日期": "date", "单位净值": "nav", "累计净值": "accumulated_nav",
            "日增长率": "daily_return", "申购状态": "subscription_status",
            "赎回状态": "redemption_status", "date": "date", "nav": "nav",
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"]).dt.date

        # Add fund_code
        df["fund_code"] = fund_code

        return df

    @with_cache
    @with_retry
    def fetch_fund_detail(self, fund_code: str) -> dict:
        """
        Fetch detailed fund information.
        Returns dict with fund metadata.
        """
        import akshare as ak
        self._rate_limit()

        detail = {
            "fund_code": fund_code,
            "fund_name": "",
            "fund_type": "",
            "management_company": "",
            "manager_name": "",
            "manager_start_date": None,
            "inception_date": None,
            "aum_yuan": None,
            "management_fee_pct": None,
            "custodian_fee_pct": None,
            "benchmark_index": "",
            "investment_style": "",
            "risk_level": "",
        }

        try:
            # Fetch fund info
            info_df = ak.fund_individual_basic_info_xq(symbol=fund_code)
            if info_df is not None and not info_df.empty:
                info_dict = dict(zip(info_df.iloc[:, 0], info_df.iloc[:, 1]))
                detail["fund_name"] = info_dict.get("基金全称", "")
                detail["fund_type"] = self._map_fund_type(info_dict.get("基金类型", ""))
                detail["management_company"] = info_dict.get("基金管理人", "")
                detail["inception_date"] = self._parse_date(info_dict.get("成立日期"))
                detail["aum_yuan"] = self.safe_float(info_dict.get("基金规模", "").replace("亿元", ""))
                detail["benchmark_index"] = info_dict.get("业绩比较基准", "")
                detail["risk_level"] = info_dict.get("风险等级", "")
        except Exception as e:
            print(f"  [Warn] fetch_fund_detail basic info failed for {fund_code}: {e}")

        # Try to get manager info
        try:
            mgr_df = ak.fund_individual_basic_info_xq(symbol=fund_code)
            # Manager info is typically part of the basic info
        except Exception:
            pass

        return detail

    @with_cache
    @with_retry
    def fetch_top_funds_by_type(self, fund_type: str = None, top_n: int = 50) -> pd.DataFrame:
        """Fetch top-performing funds, filtered by type (detected from name)."""
        import akshare as ak
        self._rate_limit()

        try:
            df = ak.fund_open_fund_rank_em(symbol="全部")
            if df is None or df.empty:
                return pd.DataFrame()

            # Actual akshare columns: 序号,基金代码,基金简称,日期,单位净值,累计净值,
            #   日增长率,近1周,近1月,近3月,近6月,近1年,近2年,近3年,
            #   今年来,成立来,手续费,起购金额,基金规模,基金经理
            col_map = {
                "基金代码": "fund_code", "基金简称": "fund_name",
                "单位净值": "nav", "日增长率": "daily_return",
                "近1周": "return_1w", "近1月": "return_1m",
                "近3月": "return_3m", "近6月": "return_6m",
                "近1年": "return_1y", "近2年": "return_2y",
                "近3年": "return_3y", "今年来": "return_ytd",
                "成立来": "return_since_inception",
                "手续费": "fee", "起购金额": "min_purchase",
                "基金规模": "aum", "基金经理": "manager_name",
            }
            df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

            # Detect fund type from name (API doesn't return type column)
            if "fund_name" in df.columns:
                df["fund_type"] = df["fund_name"].apply(self._detect_fund_type_from_name)

            # Filter by type
            if fund_type and "fund_type" in df.columns:
                df = df[df["fund_type"] == fund_type]

            # Clean numeric columns
            for col in ["return_1w", "return_1m", "return_3m", "return_6m",
                        "return_1y", "return_2y", "return_3y", "return_ytd",
                        "daily_return", "fee"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            return df.head(top_n)
        except Exception as e:
            print(f"  [Error] fetch_top_funds: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

    @staticmethod
    def _detect_fund_type_from_name(name: str) -> str:
        """Detect fund category from fund name using Chinese naming conventions."""
        if not name:
            return "混合型"
        name_lower = str(name).lower()
        # Order matters: check specific patterns first
        if any(kw in name_lower for kw in ["qdii", "海外", "全球", "纳斯达克", "标普", "港股通"]):
            return "QDII"
        if any(kw in name_lower for kw in ["货币", "现金", "活期", "日日金", "余额"]):
            return "货币型"
        if any(kw in name_lower for kw in ["纯债", "信用债", "利率债", "转债", "中短债",
                                             "短债", "债券", "债基", "国债", "金融债"]):
            return "债券型"
        if any(kw in name_lower for kw in ["etf联接", "etf", "指数", "沪深300", "中证500",
                                             "上证50", "创业板", "科创50", "科创", "纳指"]):
            return "指数型"
        if any(kw in name_lower for kw in ["混合", "灵活配置", "平衡"]):
            return "混合型"
        # Default: stock type
        return "股票型"

    @with_cache
    @with_retry
    def fetch_fund_nav_batch(self, fund_codes: list[str],
                             start_date: str = None,
                             end_date: str = None) -> dict[str, pd.DataFrame]:
        """Fetch NAV history for multiple funds."""
        results = {}
        for i, code in enumerate(fund_codes):
            try:
                print(f"  [{i+1}/{len(fund_codes)}] Fetching NAV for {code}...")
                df = self.fetch_fund_nav(code, start_date, end_date)
                if not df.empty:
                    results[code] = df
            except Exception as e:
                print(f"    Error fetching {code}: {e}")
            self._rate_limit()
        return results

    def _map_fund_type(self, raw_type: str) -> str:
        """Map raw fund type from API to standard category."""
        if not raw_type:
            return "混合型"
        for key, mapped in FUND_TYPE_MAPPING.items():
            if key in raw_type:
                return mapped
        return "混合型"  # default

    @staticmethod
    def _parse_date(val) -> date:
        """Parse various date formats."""
        if val is None:
            return None
        if isinstance(val, date):
            return val
        if isinstance(val, datetime):
            return val.date()
        for fmt in ["%Y%m%d", "%Y-%m-%d", "%Y年%m月%d日", "%Y/%m/%d"]:
            try:
                return datetime.strptime(str(val).strip(), fmt).date()
            except ValueError:
                continue
        return None
