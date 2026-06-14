"""Detailed fund information fetcher (manager, holdings, prospectus)."""

import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.fetcher.base import BaseFetcher, with_cache, with_retry


class FundDetailFetcher(BaseFetcher):
    """Fetch detailed fund metadata."""

    @with_cache
    @with_retry
    def fetch_fund_manager_history(self, fund_code: str) -> pd.DataFrame:
        """Fetch manager change history for a fund."""
        import akshare as ak
        self._rate_limit()

        try:
            df = ak.fund_individual_basic_info_xq(symbol=fund_code)
            if df is not None and not df.empty:
                return df
        except Exception:
            pass
        return pd.DataFrame()

    @with_cache
    @with_retry
    def fetch_fund_holdings(self, fund_code: str, year: str = None) -> pd.DataFrame:
        """Fetch fund's holdings (stocks/bonds the fund holds)."""
        import akshare as ak
        self._rate_limit()

        try:
            df = ak.fund_portfolio_hold_em(symbol=fund_code)
            return df if df is not None else pd.DataFrame()
        except Exception:
            return pd.DataFrame()

    @with_cache
    @with_retry
    def fetch_fund_announcements(self, fund_code: str, limit: int = 20) -> pd.DataFrame:
        """Fetch recent fund announcements."""
        import akshare as ak
        self._rate_limit()

        try:
            df = ak.fund_announcement_em(symbol=fund_code)
            if df is not None and not df.empty:
                return df.head(limit)
        except Exception:
            pass
        return pd.DataFrame()
