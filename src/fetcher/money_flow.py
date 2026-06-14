"""Fetch capital flow data (北向资金, 主力资金)."""

import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.fetcher.base import BaseFetcher, with_cache, with_retry


class MoneyFlowFetcher(BaseFetcher):
    """Fetch capital/money flow data."""

    @with_cache
    @with_retry
    def fetch_north_flow(self) -> pd.DataFrame:
        """Fetch north-bound capital flow (北向资金)."""
        import akshare as ak
        self._rate_limit()

        try:
            df = ak.stock_hsgt_north_net_flow_in_em()
            return df if df is not None else pd.DataFrame()
        except Exception:
            try:
                df = ak.stock_hsgt_hist_em(symbol="北向资金")
                return df if df is not None else pd.DataFrame()
            except Exception:
                return pd.DataFrame()

    @with_cache
    @with_retry
    def fetch_market_money_flow(self) -> pd.DataFrame:
        """Fetch market-wide money flow (主力资金流向)."""
        import akshare as ak
        self._rate_limit()

        try:
            df = ak.stock_market_fund_flow()
            return df if df is not None else pd.DataFrame()
        except Exception:
            return pd.DataFrame()

    @with_cache
    @with_retry
    def fetch_margin_trading(self) -> pd.DataFrame:
        """Fetch margin trading data (融资融券)."""
        import akshare as ak
        self._rate_limit()

        try:
            df = ak.stock_margin_detail_sse(start_period="最近一个月")
            return df if df is not None else pd.DataFrame()
        except Exception:
            return pd.DataFrame()
