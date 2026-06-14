"""Fetch sector/industry performance data."""

import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.fetcher.base import BaseFetcher, with_cache, with_retry


class SectorFetcher(BaseFetcher):
    """Fetch Chinese sector/industry performance data."""

    @with_cache
    @with_retry
    def fetch_sector_performance(self) -> pd.DataFrame:
        """Fetch 申万行业 performance data."""
        import akshare as ak
        self._rate_limit()

        try:
            # Use akshare sector/industry API
            df = ak.stock_board_industry_name_em()
            if df is not None and not df.empty:
                col_map = {
                    "板块名称": "sector_name", "板块代码": "sector_code",
                    "最新价": "close", "涨跌幅": "return_1d",
                    "总市值": "total_market_value", "换手率": "turnover_rate",
                    "上涨家数": "up_count", "下跌家数": "down_count",
                    "领涨股票": "top_stock", "领涨股票-涨跌幅": "top_stock_change",
                }
                df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
                return df
        except Exception as e:
            print(f"  [Error] fetch_sector_performance: {e}")

        return pd.DataFrame()

    @with_cache
    @with_retry
    def fetch_sector_history(self, sector_code: str, period: str = "daily") -> pd.DataFrame:
        """Fetch historical performance for a specific sector."""
        import akshare as ak
        self._rate_limit()

        try:
            df = ak.stock_board_industry_hist_em(symbol=sector_code, period=period)
            return df if df is not None else pd.DataFrame()
        except Exception:
            return pd.DataFrame()

    @with_cache
    @with_retry
    def fetch_industry_funds(self) -> pd.DataFrame:
        """Fetch industry/sector ETF performance."""
        import akshare as ak
        self._rate_limit()

        try:
            df = ak.fund_etf_category_sina(symbol="行业ETF")
            return df if df is not None else pd.DataFrame()
        except Exception:
            return pd.DataFrame()
