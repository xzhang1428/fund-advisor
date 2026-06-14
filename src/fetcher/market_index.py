"""Fetch market index data from akshare."""

import pandas as pd
import sys
from pathlib import Path
from datetime import date, datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.fetcher.base import BaseFetcher, with_cache, with_retry
from config.settings import TRACKED_INDICES


class MarketIndexFetcher(BaseFetcher):
    """Fetch Chinese market index data (上证, 沪深300, etc.)."""

    @with_cache
    @with_retry
    def fetch_index_daily(self, symbol: str, start_date: str = None,
                          end_date: str = None) -> pd.DataFrame:
        """
        Fetch daily index data from akshare.
        Args:
            symbol: Index code, e.g., '000001' for 上证指数
        Returns DataFrame with columns: date, open, high, low, close, volume, amount
        """
        import akshare as ak

        if end_date is None:
            end_date = date.today().strftime("%Y%m%d")
        if start_date is None:
            start_date = (date.today() - timedelta(days=365 * 5)).strftime("%Y%m%d")

        self._rate_limit()

        try:
            df = ak.stock_zh_index_daily(symbol=f"sh{symbol}" if symbol.startswith("000") else f"sz{symbol}")
            if df is None or df.empty:
                # Try akshare fund index endpoint
                df = ak.index_zh_a_hist(symbol=symbol, period="daily",
                                        start_date=start_date, end_date=end_date)
        except Exception:
            try:
                df = ak.index_zh_a_hist(symbol=symbol, period="daily",
                                        start_date=start_date, end_date=end_date)
            except Exception:
                # Fallback: use stock_zh_index_daily with different format
                df = ak.stock_zh_index_daily(symbol=f"sh{symbol}")

        if df is None or df.empty:
            print(f"  [Warn] No data returned for index {symbol}")
            return pd.DataFrame()

        # Normalize column names
        col_map = {
            "date": "date", "日期": "date",
            "open": "open", "开盘": "open",
            "high": "high", "最高": "high",
            "low": "low", "最低": "low",
            "close": "close", "收盘": "close",
            "volume": "volume", "成交量": "volume",
            "amount": "amount", "成交额": "amount",
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

        # Ensure date column is datetime
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"]).dt.date

        # Filter date range
        if "date" in df.columns:
            if start_date:
                s = datetime.strptime(start_date, "%Y%m%d").date()
                df = df[df["date"] >= s]
            if end_date:
                e = datetime.strptime(end_date, "%Y%m%d").date()
                df = df[df["date"] <= e]

        return df

    @with_cache
    @with_retry
    def fetch_index_valuation(self, symbol: str) -> pd.DataFrame:
        """Fetch PE/PB valuation data for an index."""
        import akshare as ak
        self._rate_limit()

        try:
            # Try to get index valuation via akshare
            df = ak.index_value_hist_funddb(symbol=symbol, indicator="市盈率")
            if df is None or df.empty:
                return pd.DataFrame()
            col_map = {"日期": "date", "市盈率": "pe", "市净率": "pb"}
            df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"]).dt.date
            return df
        except Exception:
            return pd.DataFrame()

    @with_cache
    @with_retry
    def fetch_index_live(self, symbol: str) -> dict:
        """Fetch real-time snapshot for an index."""
        import akshare as ak
        self._rate_limit()

        try:
            df = ak.stock_zh_index_spot_em()
            if df is None or df.empty:
                return {}
            row = df[df["代码"] == symbol]
            if row.empty:
                return {}
            r = row.iloc[0]
            return {
                "symbol": symbol,
                "name": r.get("名称", ""),
                "price": self.safe_float(r.get("最新价")),
                "change_pct": self.safe_float(r.get("涨跌幅")),
                "volume": self.safe_float(r.get("成交量")),
                "amount": self.safe_float(r.get("成交额")),
                "pe": self.safe_float(r.get("市盈率-动态")),
            }
        except Exception as e:
            print(f"  [Error] fetch_index_live({symbol}): {e}")
            return {}

    def fetch_all_tracked_indices(self) -> dict[str, pd.DataFrame]:
        """Fetch data for all tracked indices."""
        results = {}
        for symbol, name in TRACKED_INDICES.items():
            print(f"  Fetching {name} ({symbol})...")
            try:
                df = self.fetch_index_daily(symbol)
                if not df.empty:
                    results[symbol] = df
                    print(f"    OK: {len(df)} rows, latest: {df['date'].iloc[-1] if 'date' in df.columns else 'N/A'}")
                else:
                    print(f"    Empty result")
            except Exception as e:
                print(f"    Error: {e}")
        return results
