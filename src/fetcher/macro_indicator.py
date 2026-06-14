"""Fetch macroeconomic indicators for China."""

import pandas as pd
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.fetcher.base import BaseFetcher, with_cache, with_retry


class MacroFetcher(BaseFetcher):
    """Fetch Chinese macroeconomic indicators."""

    @with_cache
    @with_retry
    def fetch_cpi(self) -> pd.DataFrame:
        """Fetch China CPI data."""
        import akshare as ak
        self._rate_limit()

        try:
            df = ak.macro_china_cpi_yearly()
            if df is not None and not df.empty:
                return df
        except Exception:
            try:
                df = ak.macro_china_cpi_monthly()
                return df if df is not None else pd.DataFrame()
            except Exception:
                pass
        return pd.DataFrame()

    @with_cache
    @with_retry
    def fetch_pmi(self) -> pd.DataFrame:
        """Fetch China PMI data."""
        import akshare as ak
        self._rate_limit()

        try:
            df = ak.macro_china_pmi()
            return df if df is not None else pd.DataFrame()
        except Exception:
            return pd.DataFrame()

    @with_cache
    @with_retry
    def fetch_shibor(self) -> pd.DataFrame:
        """Fetch SHIBOR (interbank offered rate) data."""
        import akshare as ak
        self._rate_limit()

        try:
            df = ak.rate_interbank(market="上海银行间同业拆放利率(Shibor)")
            return df if df is not None else pd.DataFrame()
        except Exception:
            return pd.DataFrame()

    @with_cache
    @with_retry
    def fetch_m2_supply(self) -> pd.DataFrame:
        """Fetch M2 money supply data."""
        import akshare as ak
        self._rate_limit()

        try:
            df = ak.macro_china_money_supply()
            return df if df is not None else pd.DataFrame()
        except Exception:
            return pd.DataFrame()

    @with_cache
    @with_retry
    def fetch_gdp(self) -> pd.DataFrame:
        """Fetch China GDP data."""
        import akshare as ak
        self._rate_limit()

        try:
            df = ak.macro_china_gdp()
            return df if df is not None else pd.DataFrame()
        except Exception:
            return pd.DataFrame()

    @with_cache
    @with_retry
    def fetch_bond_yield(self) -> pd.DataFrame:
        """Fetch China government bond yields."""
        import akshare as ak
        self._rate_limit()

        try:
            df = ak.bond_china_yield()
            return df if df is not None else pd.DataFrame()
        except Exception:
            return pd.DataFrame()

    def fetch_all_macro(self) -> dict:
        """Fetch all macro indicators."""
        results = {}
        fetchers = {
            "CPI": self.fetch_cpi,
            "PMI": self.fetch_pmi,
            "SHIBOR": self.fetch_shibor,
            "M2": self.fetch_m2_supply,
            "GDP": self.fetch_gdp,
            "Bond_Yield": self.fetch_bond_yield,
        }
        for name, fetcher_fn in fetchers.items():
            print(f"  Fetching {name}...")
            try:
                df = fetcher_fn()
                if not df.empty:
                    results[name] = df
                    print(f"    OK: {len(df)} rows")
                else:
                    print(f"    No data (may need API key or endpoint changed)")
            except Exception as e:
                print(f"    Error: {e}")
        return results
