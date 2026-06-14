"""Historical data backfill script - fetch and store 3+ years of market data."""

import sys
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage.engine import get_session, init_database
from src.storage.repository import Repository
from src.fetcher.market_index import MarketIndexFetcher
from src.fetcher.fund_nav import FundFetcher
from config.settings import TRACKED_INDICES


def backfill_indices():
    """Backfill index data for all tracked indices."""
    print("=" * 60)
    print("  回填大盘指数历史数据")
    print("=" * 60)
    print()

    session = get_session()
    repo = Repository(session)
    fetcher = MarketIndexFetcher()

    start_date = (date.today() - timedelta(days=365 * 5)).strftime("%Y%m%d")
    end_date = date.today().strftime("%Y%m%d")

    for symbol, name in TRACKED_INDICES.items():
        print(f"  Fetching {name} ({symbol})...")
        try:
            df = fetcher.fetch_index_daily(symbol, start_date, end_date, force_refresh=True)
            if df is not None and not df.empty:
                count = 0
                for _, row in df.iterrows():
                    try:
                        repo.upsert_market_index(
                            symbol=symbol,
                            index_name=name,
                            trade_date=row.get("date", row.name) if "date" in df.columns else row.name,
                            open_=row.get("open"),
                            high=row.get("high"),
                            low=row.get("low"),
                            close=row.get("close"),
                            volume=row.get("volume"),
                            amount=row.get("amount"),
                        )
                        count += 1
                    except Exception:
                        pass
                repo.commit()
                print(f"    ✅ {name}: {count} rows stored")
            else:
                print(f"    ⚠ {name}: no data returned")
        except Exception as e:
            print(f"    ❌ {name}: {e}")

    session.close()
    print()
    print("  指数数据回填完成！")
    print("=" * 60)


def backfill_funds():
    """Backfill fund list and sample fund NAV history."""
    print()
    print("=" * 60)
    print("  回填基金数据")
    print("=" * 60)
    print()

    session = get_session()
    repo = Repository(session)
    fetcher = FundFetcher()

    # Fetch fund list
    print("  Fetching fund list...")
    try:
        df = fetcher.fetch_all_fund_list(force_refresh=True)
        if df is not None and not df.empty:
            count = 0
            for _, row in df.head(200).iterrows():
                try:
                    fund_code = str(row.get("基金代码", ""))
                    fund_type = fetcher._map_fund_type(str(row.get("基金类型", "")))
                    repo.upsert_fund_info(
                        fund_code=fund_code,
                        fund_name=str(row.get("基金简称", "")),
                        fund_type=fund_type,
                    )
                    count += 1
                except Exception:
                    pass
            repo.commit()
            print(f"    ✅ Stored {count} funds basic info")
        else:
            print("    ⚠ No fund list returned")
    except Exception as e:
        print(f"    ❌ Fund list: {e}")

    session.close()
    print()
    print("  基金数据回填完成！")
    print("=" * 60)


def main():
    """Run all backfill tasks."""
    print()
    print("🚀 基金投资顾问系统 - 数据回填")
    print(f"   日期: {date.today()}")
    print()

    # Ensure DB exists
    init_database()

    # Backfill index data
    backfill_indices()

    # Backfill fund list
    backfill_funds()

    print()
    print("✅ 所有数据回填完成！")
    print()
    print("下一步:")
    print("  1. 创建你的投资组合:")
    print('     python -m src.cli.main portfolio create --name "我的组合" --capital 100000 --profile 稳健型')
    print("  2. 分析市场:")
    print("     python -m src.cli.main analyze market")
    print("  3. 启动仪表盘:")
    print("     streamlit run dashboard/app.py")


if __name__ == "__main__":
    main()
