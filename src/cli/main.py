"""Main CLI entry point for the Fund Advisory System."""

import sys
import argparse
from pathlib import Path
from datetime import date

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.cli.formatters import (
    print_header, print_success, print_warning, print_error, print_info,
    format_cny, format_pct, portfolio_summary_table, alert_summary_table,
    regime_indicator,
)


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser."""
    parser = argparse.ArgumentParser(
        prog="fund-advisor",
        description="China Fund Advisory System - Smart fund analysis and recommendations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  fund-advisor fetch all               # Update all data
  fund-advisor analyze market          # Market analysis report
  fund-advisor analyze fund 000001     # Deep fund analysis
  fund-advisor portfolio create --name "Retirement" --capital 100000 --profile Moderate
  fund-advisor recommend funds --category Mixed --top 10
  fund-advisor recommend portfolio 1   # Generate trading signals for portfolio 1
  fund-advisor monitor check           # Check alerts
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Subcommand")

    # ---- fetch ----
    fetch_parser = subparsers.add_parser("fetch", help="Fetch data")
    fetch_subs = fetch_parser.add_subparsers(dest="fetch_target", help="Fetch target")

    fetch_subs.add_parser("all", help="Fetch all data")
    fetch_subs.add_parser("market", help="Fetch market index data")
    fetch_subs.add_parser("funds", help="Fetch fund data")
    fetch_subs.add_parser("macro", help="Fetch macro economic data")

    # ---- analyze ----
    analyze_parser = subparsers.add_parser("analyze", help="Analyze")
    analyze_subs = analyze_parser.add_subparsers(dest="analyze_target", help="Analyze target")

    analyze_market = analyze_subs.add_parser("market", help="Market analysis")
    analyze_market.add_argument("--detail", action="store_true", help="Show detailed technical indicators")

    analyze_fund = analyze_subs.add_parser("fund", help="Deep fund analysis")
    analyze_fund.add_argument("code", help="Fund code (6 digits)")

    analyze_subs.add_parser("sector", help="Sector analysis")
    analyze_subs.add_parser("valuation", help="Valuation analysis")

    # ---- portfolio ----
    portf_parser = subparsers.add_parser("portfolio", help="Portfolio management")
    portf_subs = portf_parser.add_subparsers(dest="portfolio_action", help="Action")

    portf_create = portf_subs.add_parser("create", help="Create new portfolio")
    portf_create.add_argument("--name", required=True, help="Portfolio name")
    portf_create.add_argument("--capital", type=float, required=True, help="Initial capital (CNY)")
    portf_create.add_argument("--profile", default="Moderate",
                              choices=["Conservative", "Moderate", "Balanced", "Aggressive"],
                              help="Risk profile")
    portf_create.add_argument("--description", help="Notes")

    portf_subs.add_parser("list", help="List all portfolios")

    portf_show = portf_subs.add_parser("show", help="Show portfolio details")
    portf_show.add_argument("portfolio_id", type=int, help="Portfolio ID")

    portf_add = portf_subs.add_parser("add", help="Add holding")
    portf_add.add_argument("portfolio_id", type=int, help="Portfolio ID")
    portf_add.add_argument("--fund", required=True, help="Fund code")
    portf_add.add_argument("--shares", type=float, required=True, help="Shares")
    portf_add.add_argument("--cost", type=float, required=True, help="Cost NAV")

    portf_remove = portf_subs.add_parser("remove", help="Remove holding")
    portf_remove.add_argument("portfolio_id", type=int, help="Portfolio ID")
    portf_remove.add_argument("--fund", required=True, help="Fund code")
    portf_remove.add_argument("--shares", type=float, help="Shares to sell (all if not specified)")
    portf_remove.add_argument("--price", type=float, required=True, help="Sell NAV")

    portf_rebalance = portf_subs.add_parser("rebalance", help="Rebalance analysis")
    portf_rebalance.add_argument("portfolio_id", type=int, help="Portfolio ID")

    # ---- recommend ----
    rec_parser = subparsers.add_parser("recommend", help="Recommend")
    rec_subs = rec_parser.add_subparsers(dest="recommend_target", help="Recommend type")

    rec_funds = rec_subs.add_parser("funds", help="Recommend funds")
    rec_funds.add_argument("--category", default="Mixed",
                           choices=["Stock", "Mixed", "Bond", "Index", "Money", "QDII"],
                           help="Fund category")
    rec_funds.add_argument("--top", type=int, default=10, help="Number to recommend")
    rec_funds.add_argument("--profile", default="Moderate",
                           choices=["Conservative", "Moderate", "Balanced", "Aggressive"],
                           help="Risk profile")

    rec_portfolio = rec_subs.add_parser("portfolio", help="Generate trading signals for portfolio")
    rec_portfolio.add_argument("portfolio_id", type=int, help="Portfolio ID")

    rec_allocation = rec_subs.add_parser("allocation", help="Asset allocation advice")
    rec_allocation.add_argument("--profile", default="Moderate",
                                choices=["Conservative", "Moderate", "Balanced", "Aggressive"],
                                help="Risk profile")

    # ---- monitor ----
    mon_parser = subparsers.add_parser("monitor", help="Monitor")
    mon_subs = mon_parser.add_subparsers(dest="monitor_action", help="Monitor action")

    mon_check = mon_subs.add_parser("check", help="Check alerts")
    mon_check.add_argument("--portfolio", type=int, help="Portfolio ID")

    mon_watch = mon_subs.add_parser("watch", help="Continuous monitoring mode")
    mon_watch.add_argument("--interval", type=int, default=300, help="Check interval (seconds)")
    mon_watch.add_argument("--portfolio", type=int, help="Portfolio ID")

    mon_subs.add_parser("rules", help="List alert rules")

    # ---- risk-assessment ----
    subparsers.add_parser("risk-assessment", help="Risk tolerance assessment questionnaire")

    return parser


# ---- Profile mapping (English commands -> Chinese internal values) ----
PROFILE_MAP = {
    "Conservative": "保守型",
    "Moderate": "稳健型",
    "Balanced": "平衡型",
    "Aggressive": "进取型",
}

CATEGORY_MAP = {
    "Stock": "股票型",
    "Mixed": "混合型",
    "Bond": "债券型",
    "Index": "指数型",
    "Money": "货币型",
    "QDII": "QDII",
}


def handle_fetch(args):
    """Handle fetch commands."""
    from src.storage.engine import get_session
    from src.storage.repository import Repository
    from src.fetcher.market_index import MarketIndexFetcher
    from src.fetcher.fund_nav import FundFetcher
    from src.fetcher.macro_indicator import MacroFetcher
    from src.fetcher.sector_performance import SectorFetcher

    session = get_session()
    repo = Repository(session)

    if args.fetch_target in ("all", "market"):
        print_header("Fetching Market Index Data")
        fetcher = MarketIndexFetcher()
        results = fetcher.fetch_all_tracked_indices()
        for symbol, df in results.items():
            if not df.empty:
                count = 0
                for _, row in df.tail(5).iterrows():
                    try:
                        trade_date = row.get("date") if "date" in df.columns else row.name
                        repo.upsert_market_index(
                            symbol=symbol,
                            index_name=str(row.get("index_name", symbol)),
                            trade_date=trade_date,
                            open_=float(row.get("open")) if row.get("open") else None,
                            high=float(row.get("high")) if row.get("high") else None,
                            low=float(row.get("low")) if row.get("low") else None,
                            close=float(row.get("close")) if row.get("close") else None,
                            volume=float(row.get("volume")) if row.get("volume") else None,
                            amount=float(row.get("amount")) if row.get("amount") else None,
                        )
                        count += 1
                    except Exception:
                        pass
                print(f"  {symbol}: {count} rows")
        repo.commit()
        print_success(f"Updated {len(results)} indices")

    if args.fetch_target in ("all", "funds"):
        print_header("Fetching Fund Data")
        fetcher = FundFetcher()
        try:
            funds_df = fetcher.fetch_all_fund_list(force_refresh=True)
            if funds_df is not None and not funds_df.empty:
                count = 0
                for _, row in funds_df.head(200).iterrows():
                    try:
                        fund_code = str(row.get("基金代码", ""))
                        fund_type_str = str(row.get("基金类型", ""))
                        repo.upsert_fund_info(
                            fund_code=fund_code,
                            fund_name=str(row.get("基金简称", "")),
                            fund_type=fetcher._map_fund_type(fund_type_str),
                        )
                        count += 1
                    except Exception:
                        pass
                repo.commit()
                print_success(f"Updated {count} funds")
            else:
                print_warning("No fund data returned")
        except Exception as e:
            print_warning(f"Fund fetch failed: {e}")

    if args.fetch_target in ("all", "macro"):
        print_header("Fetching Macro Data")
        fetcher = MacroFetcher()
        results = fetcher.fetch_all_macro()
        if results:
            print_success(f"Fetched {len(results)} macro indicators")
        else:
            print_warning("No macro data returned")

    session.close()


def handle_analyze(args):
    """Handle analyze commands."""
    from src.storage.engine import get_session
    from src.storage.repository import Repository
    from src.analysis.technical import TechnicalAnalyzer
    from src.analysis.market_regime import MarketRegimeDetector
    from src.analysis.valuation import ValuationAnalyzer
    import pandas as pd

    target = args.analyze_target

    if target == "market":
        print_header("Market Analysis", f"Date: {date.today()}")
        session = get_session()
        repo = Repository(session)

        name_map = {"000001": "Shanghai Composite", "000300": "CSI 300",
                     "399006": "ChiNext", "000905": "CSI 500"}

        for symbol in ["000001", "000300", "399006"]:
            rows = repo.get_index_data(symbol)
            if rows:
                df = pd.DataFrame([{
                    "date": r.trade_date,
                    "open": r.open,
                    "high": r.high,
                    "low": r.low,
                    "close": r.close,
                    "volume": r.volume,
                    "amount": r.amount,
                } for r in rows]).sort_values("date")

                if not df.empty and "close" in df.columns:
                    regime, confidence = MarketRegimeDetector.detect_regime(df)
                    print(f"  {name_map.get(symbol, symbol)}:")
                    print(f"    {regime_indicator(regime.value, confidence)}")
                    latest = df.iloc[-1]
                    prev = df.iloc[-2]["close"] if len(df) > 1 else latest["close"]
                    change = (latest["close"] / prev - 1) * 100
                    sign = "+" if change >= 0 else ""
                    print(f"    Price: {latest['close']:.2f}  Change: {sign}{change:.2f}%")

                    if rows and rows[-1].pe_ttm:
                        pe_series = pd.Series([r.pe_ttm for r in rows if r.pe_ttm])
                        current_pe = rows[-1].pe_ttm
                        pct = ValuationAnalyzer.pe_percentile(current_pe, pe_series)
                        zone = ValuationAnalyzer.valuation_zone(pct)
                        print(f"    PE: {current_pe:.2f}  PE Percentile: {pct:.0f}%  Zone: {zone}")
                    print()

        session.close()

    elif target == "fund":
        print_header(f"Fund Analysis: {args.code}")
        session = get_session()
        repo = Repository(session)
        info = repo.get_fund_info(args.code)
        if info:
            print(f"  Fund Name: {info.fund_name}")
            print(f"  Fund Type: {info.fund_type}")
            print(f"  Company:   {info.management_company or 'N/A'}")
            print(f"  Manager:   {info.manager_name or 'N/A'}")
            print(f"  Inception: {info.inception_date}")
            if info.aum_yuan:
                print(f"  AUM:       {format_cny(info.aum_yuan * 1e8)}")
            print(f"  Fee:       {info.management_fee_pct or 'N/A'}%")
            print(f"  Risk:      {info.risk_level or 'N/A'}")
        else:
            print_warning(f"Fund {args.code} not found. Please run 'fetch funds' first.")
        session.close()

    elif target == "sector":
        print_header("Sector Analysis")
        from src.fetcher.sector_performance import SectorFetcher
        fetcher = SectorFetcher()
        df = fetcher.fetch_sector_performance()
        if not df.empty:
            if "sector_name" in df.columns and "return_1d" in df.columns:
                for _, row in df.head(15).iterrows():
                    name = str(row.get("sector_name", ""))[:20]
                    ret = row.get("return_1d", 0)
                    sign = "+" if ret >= 0 else ""
                    print(f"  {name:<22s} {sign}{ret:.2f}%")
        else:
            print_warning("No sector data available")

    elif target == "valuation":
        print_header("Valuation Analysis")
        session = get_session()
        repo = Repository(session)
        for symbol, name in [("000300", "CSI 300"), ("000905", "CSI 500"), ("399006", "ChiNext")]:
            rows = repo.get_index_data(symbol)
            if rows:
                pe_vals = [r.pe_ttm for r in rows if r.pe_ttm]
                if pe_vals:
                    pe_series = pd.Series(pe_vals)
                    current_pe = pe_vals[-1]
                    pct = ValuationAnalyzer.pe_percentile(current_pe, pe_series)
                    zone = ValuationAnalyzer.valuation_zone(pct)
                    signal = ValuationAnalyzer.valuation_signal(pct)
                    print(f"  {name:<20s} PE={current_pe:.2f}  Pct={pct:.0f}%  Zone={zone}  Signal={signal}")
        session.close()


def handle_portfolio(args):
    """Handle portfolio commands."""
    from src.storage.engine import get_session
    from src.storage.repository import Repository
    from src.portfolio.manager import PortfolioManager

    session = get_session()
    repo = Repository(session)
    mgr = PortfolioManager(repo)

    if args.portfolio_action == "create":
        profile_cn = PROFILE_MAP.get(args.profile, "稳健型")
        mgr.create_portfolio(
            name=args.name,
            initial_capital=args.capital,
            risk_profile=profile_cn,
            description=args.description,
        )
    elif args.portfolio_action == "list":
        portfolios = repo.get_all_portfolios()
        if portfolios:
            for p in portfolios:
                print(f"  [{p.id}] {p.name} | Capital: {format_cny(p.initial_capital)} | "
                      f"Risk: {p.risk_profile} | Created: {p.created_at}")
        else:
            print_info("No portfolios yet. Use 'portfolio create' to create one.")

    elif args.portfolio_action == "show":
        summary = mgr.get_portfolio_summary(args.portfolio_id)
        if "error" in summary:
            print_error(summary["error"])
        else:
            print(portfolio_summary_table(summary))
            warnings = mgr.check_constraints(args.portfolio_id)
            if warnings:
                print_warning("Constraint warnings:")
                for w in warnings:
                    print(f"    {w}")

    elif args.portfolio_action == "add":
        mgr.add_holding(
            portfolio_id=args.portfolio_id,
            fund_code=args.fund,
            shares=args.shares,
            avg_cost=args.cost,
        )
        print_success(f"Added {args.fund} to portfolio {args.portfolio_id}")

    elif args.portfolio_action == "remove":
        mgr.sell_holding(
            portfolio_id=args.portfolio_id,
            fund_code=args.fund,
            shares=args.shares if args.shares else 999999999,
            price=args.price,
        )

    elif args.portfolio_action == "rebalance":
        from src.recommendation.rebalance import RebalanceEngine
        summary = mgr.get_portfolio_summary(args.portfolio_id)
        engine = RebalanceEngine()
        if engine.need_rebalance(summary.get("allocation_diff", {})):
            trades = engine.compute_rebalance_trades(summary)
            print(RebalanceEngine.format_rebalance_report(trades))
        else:
            print_success("Portfolio is within rebalancing threshold. No action needed.")

    session.close()


def handle_recommend(args):
    """Handle recommend commands."""
    from src.storage.engine import get_session
    from src.storage.repository import Repository
    from src.recommendation.scoring import MultiFactorScorer
    from src.recommendation.signal_generator import SignalGenerator
    from src.recommendation.risk_profile import RiskProfiler
    from src.portfolio.manager import PortfolioManager

    session = get_session()
    repo = Repository(session)

    if args.recommend_target == "funds":
        category_cn = CATEGORY_MAP.get(args.category, "混合型")
        print_header(f"Fund Recommendations - {category_cn}", f"Risk: {args.profile}")

        from src.fetcher.fund_nav import FundFetcher
        fetcher = FundFetcher()
        df = fetcher.fetch_top_funds_by_type(category_cn, args.top * 3)

        if not df.empty:
            funds = df.to_dict("records")
            scorer = MultiFactorScorer()
            results = scorer.score_category(funds, category_cn)
            for i, r in enumerate(results[:args.top], 1):
                name = r.get("fund_name", r.get("fund_code", ""))
                code = r.get("fund_code", "")
                score = float(r.get("total_score", 0))
                stars = "*" * min(5, int(score / 20) + 1)
                print(f"  {i:2d}. {name} ({code})")
                print(f"      {stars} Score: {score:.0f}/100 | "
                      f"Percentile: {r.get('percentile_in_category', 50):.0f}%")
                scores = r.get("scores", {})
                if scores:
                    print(f"      Return:{scores.get('return_score', 0):.0f} "
                          f"Sharpe:{scores.get('sharpe_score', 0):.0f} "
                          f"Drawdown:{scores.get('drawdown_score', 0):.0f}")
                print()
        else:
            print_warning("No fund ranking data. Please run 'fetch funds' first.")

    elif args.recommend_target == "portfolio":
        mgr = PortfolioManager(repo)
        summary = mgr.get_portfolio_summary(args.portfolio_id)
        if "error" in summary:
            print_error(summary["error"])
        else:
            scorer = MultiFactorScorer()
            gen = SignalGenerator(scorer)
            signals = gen.generate_portfolio_signals(summary)
            print(SignalGenerator.format_signal_report(signals))

    elif args.recommend_target == "allocation":
        profile_cn = PROFILE_MAP.get(args.profile, "稳健型")
        print_header(f"Asset Allocation - {profile_cn}")
        alloc = RiskProfiler.get_allocation_template(profile_cn)
        desc = RiskProfiler.profile_description(profile_cn)
        print(f"  {desc}")
        print()
        for cat, weight in alloc.items():
            if weight > 0:
                bar = "#" * int(weight * 40)
                print(f"  {cat:<8s} [{bar}] {weight:.0%}")

    session.close()


def handle_monitor(args):
    """Handle monitor commands."""
    from src.storage.engine import get_session
    from src.storage.repository import Repository
    from src.monitor.alert_engine import AlertEngine
    from src.monitor.notifier import Notifier
    from src.portfolio.manager import PortfolioManager
    from src.monitor.rules import ALL_RULES

    session = get_session()
    repo = Repository(session)

    if args.monitor_action == "rules":
        print_header("Alert Rules")
        for rule in ALL_RULES:
            print(f"  [{rule.severity.upper():<8s}] {rule.name}")
            print(f"                {rule.description}")
        print()

    elif args.monitor_action == "check":
        engine = AlertEngine(repo)
        notifier = Notifier()
        mgr = PortfolioManager(repo)

        portfolio_id = getattr(args, 'portfolio', None)
        if portfolio_id:
            summary = mgr.get_portfolio_summary(portfolio_id)
            context = AlertEngine.build_context(portfolio_summary=summary)
            alerts = engine.check_and_persist(context, portfolio_id)
        else:
            portfolios = repo.get_all_portfolios()
            alerts = []
            for p in portfolios:
                summary = mgr.get_portfolio_summary(p.id)
                context = AlertEngine.build_context(portfolio_summary=summary)
                alerts.extend(engine.check_and_persist(context, p.id))

        notifier.notify(alerts)

    elif args.monitor_action == "watch":
        import time
        engine = AlertEngine(repo)
        notifier = Notifier()
        mgr = PortfolioManager(repo)

        print_header("Continuous Monitoring", f"Interval: {args.interval}s")
        print_info("Press Ctrl+C to exit")

        try:
            while True:
                portfolio_id = getattr(args, 'portfolio', None)
                portfolio_ids = [portfolio_id] if portfolio_id else [p.id for p in repo.get_all_portfolios()]
                for pid in portfolio_ids:
                    summary = mgr.get_portfolio_summary(pid)
                    context = AlertEngine.build_context(portfolio_summary=summary)
                    alerts = engine.check_and_persist(context, pid)
                    if alerts:
                        notifier.notify(alerts)
                print(f"  [{time.strftime('%H:%M:%S')}] Monitoring... (Ctrl+C to quit)")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n  Monitoring stopped.")

    session.close()


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "risk-assessment":
        from src.recommendation.risk_profile import RiskProfiler
        RiskProfiler.run_questionnaire()
        return

    handlers = {
        "fetch": handle_fetch,
        "analyze": handle_analyze,
        "portfolio": handle_portfolio,
        "recommend": handle_recommend,
        "monitor": handle_monitor,
    }

    handler = handlers.get(args.command)
    if handler:
        try:
            handler(args)
        except KeyboardInterrupt:
            print("\n  Operation cancelled.")
        except Exception as e:
            print_error(f"Error: {e}")
            import traceback
            traceback.print_exc()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
