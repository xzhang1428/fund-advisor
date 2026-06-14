"""Daily scheduled update script for the fund advisory system."""

import sys
from pathlib import Path
from datetime import date, datetime
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage.engine import get_session, init_database
from src.storage.repository import Repository
from src.fetcher.market_index import MarketIndexFetcher
from src.fetcher.fund_nav import FundFetcher
from src.fetcher.macro_indicator import MacroFetcher
from src.monitor.alert_engine import AlertEngine
from src.monitor.notifier import Notifier
from src.portfolio.manager import PortfolioManager


def daily_update():
    """Run daily data update routine."""
    print()
    print("=" * 60)
    print(f"  📅 基金投资顾问系统 - 每日更新")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()

    session = get_session()
    repo = Repository(session)

    # 1. Fetch market index data
    print("  [1/4] 更新大盘指数数据...")
    try:
        fetcher = MarketIndexFetcher()
        results = fetcher.fetch_all_tracked_indices()
        for symbol, df in results.items():
            if not df.empty:
                for _, row in df.tail(5).iterrows():
                    try:
                        repo.upsert_market_index(
                            symbol=symbol,
                            index_name=row.get("index_name", symbol),
                            trade_date=row.get("date") if "date" in df.columns else row.name,
                            open_=row.get("open"),
                            high=row.get("high"),
                            low=row.get("low"),
                            close=row.get("close"),
                            volume=row.get("volume"),
                            amount=row.get("amount"),
                        )
                    except Exception:
                        pass
        repo.commit()
        print(f"    ✅ 更新了 {len(results)} 个指数")
    except Exception as e:
        print(f"    ❌ 指数更新失败: {e}")

    # 2. Fetch macro indicators
    print("  [2/4] 更新宏观经济数据...")
    try:
        macro = MacroFetcher()
        macro.fetch_all_macro()
        print("    ✅ 宏观数据已更新")
    except Exception as e:
        print(f"    ⚠ 宏观数据更新失败: {e}")

    # 3. Update portfolio NAVs (if holdings exist)
    print("  [3/4] 更新持仓净值...")
    try:
        portfolios = repo.get_all_portfolios()
        fund_fetcher = FundFetcher()
        for p in portfolios:
            holdings = repo.get_portfolio_holdings(p.id)
            for h in holdings[:10]:  # Limit to avoid rate issues
                try:
                    nav_df = fund_fetcher.fetch_fund_nav(h.fund_code, force_refresh=True)
                    if nav_df is not None and not nav_df.empty:
                        latest = nav_df.iloc[-1]
                        nav_val = latest.get("nav", 0)
                        nav_date = latest.get("date", date.today())
                        repo.update_holding_nav(p.id, h.fund_code, nav_val, nav_date)
                except Exception:
                    pass
        repo.commit()
        print(f"    ✅ 更新了 {sum(1 for p in portfolios for _ in repo.get_portfolio_holdings(p.id))} 个持仓")
    except Exception as e:
        print(f"    ⚠ 持仓更新失败: {e}")

    # 4. Check alerts
    print("  [4/4] 检查告警...")
    try:
        engine = AlertEngine(repo)
        notifier = Notifier()
        mgr = PortfolioManager(repo)
        all_alerts = []
        for p in portfolios:
            summary = mgr.get_portfolio_summary(p.id)
            context = AlertEngine.build_context(portfolio_summary=summary)
            alerts = engine.check_and_persist(context, p.id)
            all_alerts.extend(alerts)
        if all_alerts:
            notifier.notify(all_alerts)
            print(f"    ⚠ 触发 {len(all_alerts)} 条告警")
        else:
            print("    ✅ 未触发告警")
    except Exception as e:
        print(f"    ⚠ 告警检查失败: {e}")

    session.close()
    print()
    print("  ✅ 每日更新完成！")
    print("=" * 60)


def main():
    """Run daily update."""
    import argparse
    parser = argparse.ArgumentParser(description="基金顾问系统每日更新")
    parser.add_argument("--loop", action="store_true", help="循环模式(每N秒更新)")
    parser.add_argument("--interval", type=int, default=3600, help="循环间隔(秒), 默认3600")
    args = parser.parse_args()

    if args.loop:
        print("🔄 进入循环更新模式...")
        print(f"   更新间隔: {args.interval} 秒")
        print("   按 Ctrl+C 退出")
        try:
            while True:
                daily_update()
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n  循环更新已停止。")
    else:
        daily_update()


if __name__ == "__main__":
    main()
