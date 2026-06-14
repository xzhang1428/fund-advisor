"""Streamlit dashboard - full interactive fund advisory system."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import math
from datetime import date, timedelta
import time

st.set_page_config(
    page_title="基金投资顾问系统",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# Helper functions
# ============================================================

# Create a fresh session on each script run
from src.storage.engine import SessionLocal
from src.storage.repository import Repository
from src.storage.models import Base

# Auto-create tables on first run (critical for Streamlit Cloud)
from src.storage.engine import engine
Base.metadata.create_all(bind=engine)

_db_session = SessionLocal()
_db_repo = Repository(_db_session)

def get_repo():
    return _db_repo

def commit():
    try:
        _db_session.commit()
    except Exception:
        _db_session.rollback()
        raise

def refresh_data():
    """Force re-fresh of cached data."""
    st.cache_data.clear()
    st.rerun()

# Sidebar - always visible
st.sidebar.title("📈 基金投资顾问")
st.sidebar.markdown("---")

# Show current portfolios in sidebar
repo = get_repo()
portfolios = repo.get_all_portfolios()
if portfolios:
    st.sidebar.markdown("**我的组合**")
    for p in portfolios:
        st.sidebar.caption(f"  [{p.id}] {p.name} | {p.risk_profile}")
else:
    st.sidebar.caption("还没有组合，去「组合管理」创建")

st.sidebar.markdown("---")
st.sidebar.caption(f"数据日期: {date.today()}")
st.sidebar.caption("数据来源: akshare")

# Navigation
page = st.sidebar.radio(
    "导航",
    ["🏠 市场概览", "🔍 基金筛选", "📊 组合管理", "🎯 智能配置向导", "💡 投资建议", "⚠ 告警中心"],
)

# ============================================================
# PAGE 1: Market Overview
# ============================================================
if page == "🏠 市场概览":
    st.title("市场概览")
    st.caption("实时市场数据 · 指数行情 · 牛熊判断")

    try:
        from src.analysis.market_regime import MarketRegimeDetector
        from src.analysis.valuation import ValuationAnalyzer

        index_config = {
            "000001": "上证指数", "000300": "沪深300",
            "399006": "创业板指", "000905": "中证500",
        }

        # Metric cards row
        cols = st.columns(len(index_config))
        regime_results = {}

        for i, (symbol, name) in enumerate(index_config.items()):
            rows = repo.get_index_data(symbol)
            if rows:
                df = pd.DataFrame([{
                    "date": r.trade_date, "close": r.close,
                    "open": r.open, "high": r.high, "low": r.low,
                    "volume": r.volume, "amount": r.amount,
                    "pe_ttm": r.pe_ttm,
                } for r in rows]).sort_values("date")

                if not df.empty and "close" in df.columns:
                    regime, conf = MarketRegimeDetector.detect_regime(df)
                    latest = df.iloc[-1]
                    prev = df.iloc[-2]["close"] if len(df) > 1 else latest["close"]
                    change_pct = (latest["close"] / prev - 1) * 100

                    with cols[i]:
                        sign = "+" if change_pct >= 0 else ""
                        color = "normal"  # streamlit default
                        st.metric(
                            name,
                            f"{latest['close']:.2f}",
                            f"{sign}{change_pct:.2f}%",
                        )
                        reg_label = "牛" if "Bull" in str(regime) else ("熊" if "Bear" in str(regime) else "震")
                        st.caption(f"{reg_label} | PE:{latest.get('pe_ttm', 'N/A')}" if latest.get('pe_ttm') else reg_label)
                    regime_results[symbol] = {"regime": regime, "confidence": conf, "df": df}

        # Charts row
        st.markdown("---")
        st.subheader("指数走势对比")
        chart_cols = st.columns(2)
        for i, (symbol, name) in enumerate([("000001", "上证指数"), ("000300", "沪深300")]):
            r = regime_results.get(symbol, {})
            df = r.get("df")
            if df is not None and not df.empty:
                with chart_cols[i]:
                    df_recent = df.tail(120)  # ~6 months
                    st.line_chart(df_recent.set_index("date")["close"], height=300)

        # Refresh button
        if st.button("🔄 刷新数据", help="重新拉取最新行情"):
            with st.spinner("正在获取最新数据..."):
                try:
                    from src.fetcher.market_index import MarketIndexFetcher
                    fetcher = MarketIndexFetcher()
                    results = fetcher.fetch_all_tracked_indices()
                    for symbol, df in results.items():
                        if not df.empty:
                            for _, row in df.tail(5).iterrows():
                                try:
                                    repo.upsert_market_index(
                                        symbol=symbol,
                                        index_name=str(row.get("index_name", symbol)),
                                        trade_date=row.get("date") if "date" in df.columns else row.name,
                                        close=float(row.get("close")) if row.get("close") else None,
                                        volume=float(row.get("volume")) if row.get("volume") else None,
                                    )
                                except Exception:
                                    pass
                    commit()
                    st.success(f"已更新 {len(results)} 个指数")
                    st.rerun()
                except Exception as e:
                    st.error(f"刷新失败: {e}")

    except Exception as e:
        st.warning(f"数据加载中，请先执行数据更新: {e}")

# ============================================================
# PAGE 2: Fund Screener
# ============================================================
elif page == "🔍 基金筛选":
    st.title("基金筛选")
    st.caption("了解各类基金特点，按类型筛选排名靠前的基金")

    # ─── Fund Category Guide ───
    with st.expander("📖 基金类型说明（点击展开）", expanded=True):
        guides = st.columns(3)
        category_info = [
            ("股票型", "高风险高收益", "股票仓位≥80%，牛市涨得多、熊市跌得狠。适合能承受大幅波动的投资者。", "🔥 高风险"),
            ("混合型", "灵活配置", "股票债券灵活调配，经理可根据市场调整仓位。震荡市首选，攻守兼备。", "⚡ 中高风险"),
            ("指数型", "被动跟踪指数", "跟踪沪深300/中证500等指数，费率最低。适合定投和估值玩法（低估买、高估卖）。", "📊 中高风险"),
            ("债券型", "稳健收益", "主要投国债/企业债，波动小收益稳。熊市避风港，降息周期受益。", "🛡 中低风险"),
            ("货币型", "现金管理", "投短期存款/票据，流动性好。收益略高于银行活期，几乎不亏损。", "💰 低风险"),
            ("QDII", "海外投资", "投美股/港股/全球市场，分散A股单一市场风险。需注意汇率波动。", "🌍 中高风险"),
        ]
        for i, (name, tagline, desc, risk) in enumerate(category_info):
            with guides[i % 3]:
                st.markdown(f"**{name}** — {tagline}")
                st.caption(desc)
                st.caption(risk)

    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    with col1:
        category = st.selectbox("选择要筛选的基金类型", ["混合型", "股票型", "债券型", "指数型", "货币型", "QDII"])
    with col2:
        top_n = st.slider("显示数量", 5, 30, 10)
    with col3:
        st.write("")
        st.write("")
        search_btn = st.button("🔍 开始筛选", use_container_width=True, type="primary")

    if search_btn:
        with st.spinner(f"正在从天天基金获取 {category} 排名数据..."):
            try:
                from src.fetcher.fund_nav import FundFetcher
                from src.recommendation.scoring import MultiFactorScorer

                fetcher = FundFetcher()
                # Force refresh to get latest data
                df = fetcher.fetch_top_funds_by_type(category, top_n * 3)

                if df is not None and not df.empty:
                    st.success(f"获取到 {len(df)} 只基金，正在多因子评分...")

                    funds_list = df.to_dict("records")
                    scorer = MultiFactorScorer()
                    scored = scorer.score_category(funds_list, category)

                    st.markdown(f"### 🏆 {category} TOP {min(top_n, len(scored))}")
                    st.caption("评分综合考虑：收益能力(35%) + 风险控制(30%) + 管理质量(15%) + 规模适配(5%) + 市场适配(15%)")

                    for i, r in enumerate(scored[:top_n], 1):
                        code = r.get("fund_code", "")
                        name = r.get("fund_name", code)
                        total = r.get("total_score", 50)
                        scores = r.get("scores", {})

                        # Star rating
                        stars = "★" * max(1, int(total / 20)) + "☆" * (5 - max(1, int(total / 20)))

                        with st.container():
                            c1, c2 = st.columns([3, 1])
                            with c1:
                                st.markdown(f"### {i}. {name}")
                                st.caption(f"代码: {code} | {stars} | 综合评分: **{total:.0f}/100** | 同类排名: 前 **{r.get('percentile_in_category', 50):.0f}%**")
                            with c2:
                                buy_placeholder = st.empty()  # for potential buy button

                            # Detailed scoring breakdown
                            score_cols = st.columns(4)
                            with score_cols[0]:
                                ret_s = scores.get("return_score", 0)
                                st.metric("收益能力", f"{ret_s:.0f}", help="近1年+近3年收益表现")
                            with score_cols[1]:
                                sharpe_s = scores.get("sharpe_score", 0)
                                dd_s = scores.get("drawdown_score", 0)
                                st.metric("风险控制", f"{(sharpe_s+dd_s)//2:.0f}", help="夏普比率+最大回撤")
                            with score_cols[2]:
                                mgr_s = scores.get("manager_score", 0)
                                fee_s = scores.get("fee_score", 0)
                                st.metric("管理质量", f"{(mgr_s+fee_s)//2:.0f}", help="经理经验+费率")
                            with score_cols[3]:
                                fit_s = scores.get("market_fit_score", 50)
                                st.metric("市场适配", f"{fit_s:.0f}", help=f"{category}在当前市场环境下的适配度")

                            # Why this fund?
                            reasons = []
                            if ret_s >= 70:
                                reasons.append("历史收益表现优秀")
                            elif ret_s >= 50:
                                reasons.append("收益表现良好")
                            if dd_s >= 70:
                                reasons.append("回撤控制出色，抗跌能力强")
                            elif dd_s >= 50:
                                reasons.append("回撤控制较好")
                            if mgr_s >= 70:
                                reasons.append("基金经理经验丰富")
                            if fee_s >= 70:
                                reasons.append("费率较低，长期持有成本优势明显")
                            if fit_s >= 70:
                                reasons.append(f"当前市场环境下{category}配置价值较高")
                            elif fit_s >= 50:
                                reasons.append(f"{category}在当前市场适配度适中")

                            if reasons:
                                st.caption("💡 " + "；".join(reasons))

                            st.markdown("---")

                else:
                    st.error(f"未能获取 {category} 数据")
                    st.info("**可能原因：** 1) 网络问题  2) 天天基金接口限流")
                    st.info("**解决办法：** 在终端运行一次数据拉取\n```\nexport PYTHONUTF8=1\ncd /c/Users/张可心/fund-advisory-system\n/d/python/python.exe -m src.cli.main fetch funds\n```")
                    st.info("然后回到页面重新点击筛选按钮")

            except Exception as e:
                st.error(f"获取失败: {str(e)[:200]}")
                st.info("请在终端运行: python -m src.cli.main fetch funds")

# ============================================================
# PAGE 3: Portfolio Management (FULL CRUD)
# ============================================================
elif page == "📊 组合管理":
    st.title("组合管理")
    st.caption("创建组合 · 管理持仓 · 查看盈亏 · 再平衡")

    from src.portfolio.manager import PortfolioManager
    from src.recommendation.rebalance import RebalanceEngine
    mgr = PortfolioManager(repo)

    # ─── Tabs for different operations ───
    tab1, tab2, tab3, tab4 = st.tabs(["📋 查看组合", "➕ 添加买入", "➖ 卖出减仓", "🔄 再平衡"])

    # ─── TAB 1: View Portfolio ───
    with tab1:
        portfolios = repo.get_all_portfolios()
        if not portfolios:
            st.warning("还没有组合，在下方直接创建")
            st.markdown("---")
            with st.form("tab1_create_form"):
                st.markdown("### 创建你的第一个组合")
                c1, c2 = st.columns(2)
                with c1:
                    t1_name = st.text_input("组合名称", placeholder="例如: 我的退休金", key="t1_name")
                    t1_capital = st.number_input("初始资金 (元)", min_value=1000.0, value=100000.0, step=10000.0, key="t1_cap")
                with c2:
                    t1_profile = st.selectbox("风险偏好", ["稳健型", "保守型", "平衡型", "进取型"], key="t1_prof")
                    t1_desc = st.text_input("备注 (可选)", key="t1_desc")
                if st.form_submit_button("✅ 创建组合", type="primary", use_container_width=True):
                    if t1_name:
                        mgr.create_portfolio(name=t1_name, initial_capital=t1_capital, risk_profile=t1_profile, description=t1_desc)
                        st.success(f"组合 '{t1_name}' 创建成功！")
                        st.rerun()
                    else:
                        st.error("请输入组合名称")
        else:
            p_names = {f"[{p.id}] {p.name} ({p.risk_profile})": p.id for p in portfolios}
            selected_p = st.selectbox("选择组合", list(p_names.keys()), key="view_select")
            pid = p_names[selected_p]

            summary = mgr.get_portfolio_summary(pid)
            if "error" in summary:
                st.error(summary["error"])
            else:
                # Metrics row
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.metric("当前市值", f"¥{summary.get('current_value', 0):,.2f}")
                with c2:
                    ret = summary.get('total_return', 0)
                    st.metric("总收益率", f"{ret*100:+.2f}%")
                with c3:
                    st.metric("持仓数量", summary.get('holdings_count', 0))
                with c4:
                    st.metric("风险偏好", summary.get('risk_profile', 'N/A'))

                # Holdings table
                st.subheader("持仓明细")
                holdings = summary.get("holdings", [])
                if holdings:
                    h_data = []
                    for h in holdings:
                        h_data.append({
                            "基金名称": h.get("fund_name", h.get("fund_code", "")),
                            "代码": h.get("fund_code", ""),
                            "份额": f"{h.get('shares', 0):,.0f}",
                            "成本价": f"{h.get('avg_cost', 0):.4f}",
                            "现价": f"{h.get('current_nav', 0):.4f}" if h.get('current_nav') else "-",
                            "市值": f"¥{h.get('market_value', 0):,.2f}",
                            "盈亏": f"{h.get('pnl_pct', 0)*100:+.1f}%",
                            "占比": f"{h.get('weight', 0)*100:.1f}%",
                        })
                    st.dataframe(pd.DataFrame(h_data), use_container_width=True, hide_index=True)

                    # Allocation pie chart
                    alloc = summary.get("allocation", {})
                    target_alloc = summary.get("target_allocation", {})
                    if alloc:
                        st.subheader("资产配置")
                        col_pie, col_target = st.columns([1, 1])
                        with col_pie:
                            import plotly.express as px
                            fig = px.pie(
                                names=list(alloc.keys()),
                                values=list(alloc.values()),
                                title="实际配置",
                                hole=0.4,
                            )
                            st.plotly_chart(fig, use_container_width=True)
                        with col_target:
                            if target_alloc:
                                fig2 = px.pie(
                                    names=list(target_alloc.keys()),
                                    values=list(target_alloc.values()),
                                    title="目标配置",
                                    hole=0.4,
                                )
                                st.plotly_chart(fig2, use_container_width=True)

                # Constraint warnings
                warnings = mgr.check_constraints(pid)
                if warnings:
                    st.subheader("⚠ 约束检查")
                    for w in warnings:
                        if "STOP" in w:
                            st.error(w)
                        else:
                            st.warning(w)

                # Delete button
                with st.expander("🗑 删除组合"):
                    if st.button("确认删除此组合", type="primary", key="delete_portfolio"):
                        mgr.delete_portfolio(pid)
                        st.success("组合已删除")
                        st.rerun()

    # ─── TAB 2: Add Holding / Create Portfolio ───
    with tab2:
        st.subheader("创建新组合 或 买入基金")

        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("**创建新组合**")
            with st.form("create_portfolio_form"):
                new_name = st.text_input("组合名称", placeholder="例如: 我的退休金")
                new_capital = st.number_input("初始资金 (元)", min_value=1000.0, value=100000.0, step=10000.0)
                new_profile = st.selectbox("风险偏好", ["稳健型", "保守型", "平衡型", "进取型"])
                new_desc = st.text_input("备注 (可选)")
                if st.form_submit_button("✅ 创建组合", use_container_width=True):
                    if new_name:
                        mgr.create_portfolio(
                            name=new_name,
                            initial_capital=new_capital,
                            risk_profile=new_profile,
                            description=new_desc,
                        )
                        st.success(f"组合 '{new_name}' 创建成功！")
                        st.rerun()
                    else:
                        st.error("请输入组合名称")

        with col_b:
            st.markdown("**买入基金**")
            portfolios = repo.get_all_portfolios()
            if not portfolios:
                st.caption("请先创建组合")
            else:
                with st.form("add_holding_form"):
                    p_sel = st.selectbox(
                        "选择组合",
                        [p.id for p in portfolios],
                        format_func=lambda x: f"[{x}] {repo.get_portfolio(x).name}",
                    )
                    fund_code = st.text_input("基金代码", placeholder="6位代码，如 110011")
                    shares = st.number_input("购买份额", min_value=1.0, value=1000.0, step=1000.0)
                    cost = st.number_input("买入净值 (元/份)", min_value=0.01, value=1.0000, step=0.01, format="%.4f")
                    note = st.text_input("备注 (可选)")
                    if st.form_submit_button("💰 确认买入", use_container_width=True):
                        if fund_code and len(fund_code) == 6:
                            mgr.add_holding(
                                portfolio_id=p_sel,
                                fund_code=fund_code,
                                shares=shares,
                                avg_cost=cost,
                                notes=note,
                            )
                            st.success(f"买入 {fund_code} × {shares:,.0f} 份，成本 ¥{cost:.4f}")
                            st.rerun()
                        else:
                            st.error("请输入正确的6位基金代码")

    # ─── TAB 3: Sell / Reduce ───
    with tab3:
        st.subheader("卖出/减仓基金")
        portfolios = repo.get_all_portfolios()
        if not portfolios:
            st.info("还没有组合")
        else:
            p_sel = st.selectbox(
                "选择组合",
                [p.id for p in portfolios],
                format_func=lambda x: f"[{x}] {repo.get_portfolio(x).name}",
                key="sell_portfolio",
            )

            hold_list = repo.get_portfolio_holdings(p_sel)
            if not hold_list:
                st.caption("该组合没有持仓")
            else:
                with st.form("sell_holding_form"):
                    fund_opts = {f"{h.fund_code}（持有 {h.shares:,.0f} 份, 成本 ¥{h.avg_cost:.4f}）": h
                                 for h in hold_list}
                    selected = st.selectbox("选择要卖出的基金", list(fund_opts.keys()))
                    h = fund_opts[selected]

                    sell_all = st.checkbox("全部卖出", value=True)
                    sell_shares = None if sell_all else st.number_input(
                        "卖出份额", min_value=1.0, max_value=float(h.shares), step=100.0,
                    )
                    sell_price = st.number_input("卖出净值 (元/份)", min_value=0.01, value=float(h.avg_cost), step=0.01, format="%.4f")

                    actual_shares = h.shares if sell_all else (sell_shares or h.shares)
                    actual_amount = actual_shares * sell_price

                    st.caption(f"预计收回: ¥{actual_amount:,.2f}")

                    if st.form_submit_button("💸 确认卖出", use_container_width=True):
                        mgr.sell_holding(
                            portfolio_id=p_sel,
                            fund_code=h.fund_code,
                            shares=actual_shares,
                            price=sell_price,
                        )
                        st.success(f"卖出 {h.fund_code} × {actual_shares:,.0f} 份，收回 ¥{actual_amount:,.2f}")
                        st.rerun()

    # ─── TAB 4: Rebalance ───
    with tab4:
        st.subheader("组合再平衡")
        st.caption("检查当前配置与目标配置的偏差，给出调仓建议")

        portfolios = repo.get_all_portfolios()
        if portfolios:
            p_sel = st.selectbox(
                "选择组合",
                [p.id for p in portfolios],
                format_func=lambda x: f"[{x}] {repo.get_portfolio(x).name}",
                key="rebalance_portfolio",
            )
            if st.button("🔍 分析再平衡需求"):
                summary = mgr.get_portfolio_summary(p_sel)
                engine = RebalanceEngine()
                alloc_diff = summary.get("allocation_diff", {})

                if engine.need_rebalance(alloc_diff):
                    trades = engine.compute_rebalance_trades(summary)
                    st.subheader("建议调仓操作")
                    trade_data = []
                    for t in trades:
                        trade_data.append({
                            "操作": t.get("action", ""),
                            "类别": t.get("category", ""),
                            "金额": f"¥{t.get('trade_amount', 0):,.2f}",
                            "当前权重": f"{t.get('current_weight', 0):.1%}",
                            "目标权重": f"{t.get('target_weight', 0):.1%}",
                            "偏差": f"{t.get('drift', 0):.1%}",
                        })
                    st.dataframe(pd.DataFrame(trade_data), use_container_width=True, hide_index=True)

                    total_buy = sum(t.get("trade_amount", 0) for t in trades if t.get("trade_type") == "BUY")
                    total_sell = sum(t.get("trade_amount", 0) for t in trades if t.get("trade_type") == "SELL")
                    st.caption(f"需卖出约 ¥{total_sell:,.2f}，买入约 ¥{total_buy:,.2f}")
                else:
                    st.success("当前持仓在再平衡阈值内，无需调整")
        else:
            st.info("还没有组合")

# ============================================================
# PAGE 4: Smart Investment Wizard (NEW)
# ============================================================
elif page == "🎯 智能配置向导":
    st.title("🎯 智能配置向导")
    st.caption("输入资金 → 选择风险偏好 → 获取推荐基金 → 一键加入组合")

    from src.recommendation.risk_profile import RiskProfiler
    from src.recommendation.scoring import MultiFactorScorer
    from src.fetcher.fund_nav import FundFetcher
    from src.portfolio.manager import PortfolioManager

    # ─── Step 1: settings ───
    st.subheader("第一步：设定你的资金和风险偏好")
    col1, col2 = st.columns(2)
    with col1:
        w_capital = st.number_input("你的可投资资金 (元)", min_value=1000.0, value=100000.0, step=10000.0, key="wiz_cap")
    with col2:
        w_profile = st.selectbox("风险偏好", ["稳健型", "保守型", "平衡型", "进取型"], key="wiz_prof")

    alloc = RiskProfiler.get_allocation_template(w_profile)
    st.markdown("**建议资产配置：**")
    acols = st.columns(6)
    for i, (cat, w) in enumerate(alloc.items()):
        with acols[i]:
            st.metric(cat, f"{w:.0%}")

    st.markdown("---")

    # ─── Step 2: search ───
    st.subheader("第二步：获取推荐基金")
    w_force = st.checkbox("强制刷新数据（重新从天天基金拉取）", key="wiz_force")

    if st.button("🚀 开始智能推荐", type="primary", use_container_width=True, key="wiz_search"):
        with st.spinner("正在从天天基金拉取数据并分析..."):
            try:
                fetcher = FundFetcher()
                scorer = MultiFactorScorer()
                all_recs = []

                for cat, weight in alloc.items():
                    if weight <= 0.01:
                        continue
                    df = fetcher.fetch_top_funds_by_type(cat, 15, force_refresh=w_force)
                    if df is None or df.empty:
                        st.warning(f"{cat} 暂无数据")
                        continue
                    funds = df.to_dict("records")
                    scored = scorer.score_category(funds, cat)
                    n = max(1, int(weight * 12))
                    for r in scored[:n]:
                        r["_cat"] = cat
                        r["_amount"] = w_capital * weight / n
                        all_recs.append(r)

                # Save to session_state so it survives reruns
                st.session_state['wizard_recs'] = all_recs
                st.session_state['wizard_cap'] = w_capital
                st.session_state['wizard_prof'] = w_profile
                st.rerun()

            except Exception as e:
                st.error(f"获取失败: {str(e)[:300]}")
                import traceback
                st.code(traceback.format_exc())

    # ─── Step 3: display results from session_state ───
    all_recs = st.session_state.get('wizard_recs')
    # Clear stale data that doesn't have the expected fields
    if all_recs and len(all_recs) > 0 and '_cat' not in all_recs[0]:
        st.session_state['wizard_recs'] = None
        all_recs = None
    if all_recs:
        st.success(f"共推荐 {len(all_recs)} 只基金")
        st.markdown("---")
        st.subheader("第三步：查看推荐详情，选择要买入的基金")

        # Portfolio selector (NOT in a form)
        portfolios = repo.get_all_portfolios()
        create_new = st.checkbox("创建新组合", value=(len(portfolios) == 0), key="wiz_new")
        if create_new:
            target_name = st.text_input("新组合名称", value=f"智能组合-{st.session_state.get('wizard_prof','稳健型')}-{date.today()}", key="wiz_name")
        else:
            if portfolios:
                p_opts = {f"[{p.id}] {p.name} ({p.risk_profile})": p.id for p in portfolios}
                sel = st.selectbox("选择已有组合", list(p_opts.keys()), key="wiz_sel")

        st.markdown("---")

        # Fund cards
        selected_flags = {}
        for i, r in enumerate(all_recs):
            code = r.get("fund_code", "")
            name = r.get("fund_name", code)
            cat = r.get("_cat", "")
            score = r.get("total_score", 50)
            amount = r.get("_amount", 0)
            s = r.get("scores", {})

            # ---- Holding period & review cadence (months) ----
            hold_map = {
                "债券型": ("持有 12-36 个月", "波动小收益稳，底仓配置", "每季度看一眼即可"),
                "指数型": ("持有 24-60 个月", "定投穿越牛熊，低估多投高估少投", "每月定投日操作一次"),
                "货币型": ("随时可取", "现金管理工具，用钱时赎回", "无需审查"),
                "QDII": ("持有 24-36 个月", "海外周期不同A股，汇率需平滑", "每季度审视一次"),
                "股票型": ("持有 24-60 个月", "短期易亏，持有越久盈利概率越高", "每月审视一次，按兵不动为主"),
            }
            base_hold, hold_reason, review_freq = hold_map.get(
                cat, ("持有 12-36 个月", "混合基金灵活调配", "每月审视一次，按季调整")
            )

            # A/C detection
            share_class = "A" if name.endswith("A") else ("C" if name.endswith("C") else "")
            if share_class == "A":
                fee_note = " | A类费率最优，长期持有成本最低"
            elif share_class == "C":
                fee_note = " | C类免申购费但年费更高，超1年不划算"
            else:
                fee_note = ""

            # Full holding display string
            hold_str = f"📅 建议持有 **{base_hold}**{fee_note} — {hold_reason}"

            # Render fund card
            with st.container():
                c_name, c_score, c_amount = st.columns([3, 0.8, 0.8])
                with c_name:
                    selected_flags[i] = st.checkbox(
                        f"**{name}** ({code}) | {cat} | 综合评分 {score:.0f}/100",
                        value=True, key=f"wiz_chk_{i}"
                    )
                with c_score:
                    st.metric("评分", f"{score:.0f}")
                with c_amount:
                    st.metric("金额", f"¥{amount:,.0f}")
                # Holding period and review frequency
                st.markdown(f"> 📅 **{base_hold}**{fee_note}  |  🔍 {review_freq}")
                st.caption(f"  {hold_reason}")
            st.markdown("---")

        # Count and confirm
        selected_count = sum(1 for i in range(len(all_recs)) if selected_flags.get(i, True))
        total_amt = sum(all_recs[i]["_amount"] for i in range(len(all_recs)) if selected_flags.get(i, True))
        st.markdown(f"**已选 {selected_count} 只，合计 ¥{total_amt:,.0f}**")

        if st.button("✅ 确认买入以上基金", type="primary", use_container_width=True):
            mgr = PortfolioManager(repo)
            if create_new:
                p = mgr.create_portfolio(
                    name=target_name,
                    initial_capital=st.session_state.get('wizard_cap', 100000),
                    risk_profile=st.session_state.get('wizard_prof', '稳健型'),
                )
                pid = p.id
            else:
                pid = p_opts[sel]

            errors = []
            added = 0
            for i, r in enumerate(all_recs):
                if selected_flags.get(i, True):
                    try:
                        code = r.get("fund_code", "")
                        name = r.get("fund_name", "")
                        cat = r.get("_cat", "")
                        amount = r.get("_amount", 0)
                        repo.upsert_fund_info(code, name, cat)
                        mgr.add_holding(pid, code, amount, 1.0)
                        added += 1
                    except Exception as e:
                        errors.append(f"{code}: {e}")

            if errors:
                st.error(f"部分失败: {'; '.join(errors)}")
            else:
                st.success(f"✅ 成功买入 {added} 只基金！去「📊 组合管理」查看")
                st.balloons()
                st.session_state['wizard_recs'] = None
                st.rerun()

    # If no recs yet, show guide
    if not all_recs:
        st.markdown("---")
        with st.expander("📖 风险偏好参考", expanded=False):
            st.markdown("**保守型**: 保本优先，主配货币+债券，适合退休人士")
            st.markdown("**稳健型**: 稳健增值，股债均衡，适合大多数普通投资者")
            st.markdown("**平衡型**: 平衡增长，权益60-70%，适合有经验投资者")
            st.markdown("**进取型**: 追求高收益，权益80%+，适合长期投资")

elif page == "💡 投资建议":
    st.title("持仓监测与决策建议")

    # ─── Advice framework explanation ───
    with st.expander("📖 本建议的分析框架（点击了解）", expanded=False):
        st.markdown("""
        **这是一个月频决策系统，不是日频交易工具。**

        | 分析层级 | 时间范围 | 数据来源 | 决策权重 |
        |---|---|---|---|
        | 🔍 短期观察 | 日涨跌、近一周 | 净值走势 | 仅供参考，不直接触发操作 |
        | 📊 中期判断 | 近一月、近三月 | 净值走势 | **主要决策依据**（权重60%） |
        | 🏔 长期视角 | 近一年、持有时间 | 净值走势+持仓记录 | 趋势验证（权重40%） |

        **操作节奏建议：**
        - 「加仓/减仓」= 本月内关注机会，不是明天就要操作
        - 「卖出」= 本周内尽快处理（意味着风险信号较强）
        - 「持有」= 按兵不动，下个月再审视

        **关键理念：**
        - 日涨跌只是噪音，不要被单日波动影响判断
        - 一周涨跌3%以内属正常波动，权益类基金尤其如此
        - 只有连续数周同向运动或重大基本面变化才值得行动
        - 持有时间越长，短期波动的操作意义越小
        """)

    st.caption("月频决策 · 中期趋势为主 · 短期波动仅为参考")

    from src.portfolio.manager import PortfolioManager
    from src.recommendation.scoring import MultiFactorScorer
    from src.fetcher.fund_nav import FundFetcher

    portfolios = repo.get_all_portfolios()
    if not portfolios:
        st.info("还没有组合，去「组合管理」或「智能配置向导」创建")
    else:
        mgr = PortfolioManager(repo)
        p_sel = st.selectbox(
            "选择组合",
            [p.id for p in portfolios],
            format_func=lambda x: f"[{x}] {repo.get_portfolio(x).name} ({repo.get_portfolio(x).risk_profile})",
            key="advice_portfolio",
        )

        force_refresh = st.checkbox("强制刷新净值数据", help="重新拉取每只基金最新净值")

        if st.button("🔍 分析持仓并生成建议", type="primary", use_container_width=True):
            summary = mgr.get_portfolio_summary(p_sel)
            if "error" in summary:
                st.error(summary["error"])
            else:
                holdings = summary.get("holdings", [])
                if not holdings:
                    st.info("该组合暂时没有持仓")
                else:
                    st.success(f"正在分析 {len(holdings)} 只持仓...")
                    fetcher = FundFetcher()

                    advice_list = []
                    for h in holdings:
                        code = h.get("fund_code", "")
                        name = h.get("fund_name", code)
                        shares = h.get("shares", 0)
                        cost = h.get("avg_cost", 0)
                        mkt_val = h.get("market_value", 0)
                        weight = h.get("weight", 0)
                        pnl_pct = h.get("pnl_pct", 0)
                        fund_type = h.get("fund_type", "未知")

                        # Fetch recent NAV data
                        ret_1w = ret_1m = ret_3m = ret_1y = None
                        ret_1d = None
                        nav_ok = False
                        try:
                            nav_df = fetcher.fetch_fund_nav(code, force_refresh=force_refresh)
                            if nav_df is not None and not nav_df.empty and "daily_return" in nav_df.columns:
                                nav_ok = True
                                df = nav_df.sort_values("date") if "date" in nav_df.columns else nav_df
                                returns = pd.to_numeric(df["daily_return"], errors="coerce").dropna()
                                if len(returns) >= 5:
                                    ret_1d = float(returns.iloc[-1]) if len(returns) >= 1 else None
                                    ret_1w = float(returns.iloc[-5:].sum()) if len(returns) >= 5 else None
                                    ret_1m = float(returns.iloc[-22:].sum()) if len(returns) >= 22 else None
                                    ret_3m = float(returns.iloc[-66:].sum()) if len(returns) >= 66 else None
                                    ret_1y = float(returns.iloc[-242:].sum()) if len(returns) >= 242 else None
                        except Exception:
                            pass

                        # ---- Multi-dimension decision engine ----
                        signal = "持有"
                        urgency = 0
                        reasons = []
                        warnings = []
                        tips = []

                        # ---- 维度0: 持有时间与操作节奏 ----
                        from datetime import date as dt_date
                        purchase_date = h.get("purchase_date")
                        holding_days = None
                        if purchase_date:
                            if isinstance(purchase_date, str):
                                purchase_date = dt_date.fromisoformat(purchase_date)
                            holding_days = (dt_date.today() - purchase_date).days

                        # Determine the appropriate action rhythm
                        if holding_days is not None:
                            if holding_days < 7:
                                tips.append(f"刚买入仅 {holding_days} 天，短期波动属正常。基金投资至少看3-6个月，不要因为几天的涨跌就操作")
                                urgency = max(0, urgency - 3)  # suppress urgency for newly bought
                            elif holding_days < 30:
                                tips.append(f"持有 {holding_days} 天，仍在建仓观察期。建议至少持有1个月再考虑调整")
                                urgency = max(0, urgency - 2)
                            elif holding_days < 90:
                                tips.append(f"持有约 {holding_days//30} 个月，趋势初步形成但还不够稳定。每季度审视一次即可")
                                urgency = max(0, urgency - 1)
                            elif holding_days < 365:
                                tips.append(f"持有约 {holding_days//30} 个月，可结合中短期趋势判断。每月审视一次，不必频繁操作")
                            elif holding_days < 730:
                                tips.append(f"持有约 {holding_days//365} 年，已有较长的业绩记录。评估是否仍符合最初的投资逻辑")
                            else:
                                tips.append(f"持有超 {holding_days//365} 年，长期投资者。关注基金是否发生根本性变化（经理更换、策略漂移），而非短期波动")
                        else:
                            tips.append("无法确定首次购买日期，建议记录买入时间以便跟踪持有周期")

                        # Action rhythm reminder
                        if "股票" in fund_type or "指数" in fund_type:
                            tips.append("权益类基金建议持有2年以上，短期波动3%-5%属常态，日常无需关注，每月看一眼即可")
                        if "债券" in fund_type:
                            tips.append("债券基金波动小，每季度审视一次即可，无需频繁操作")
                        if "混合" in fund_type:
                            tips.append("混合基金每月审视一次配置逻辑，不需要每日看盘")

                        # ---- 维度1: 中期走势分析（月频决策，周数据仅为参考）----
                        if nav_ok and ret_1m is not None:
                            if ret_1m > 10:
                                reasons.append(f"近一月涨 {ret_1m:+.1f}%，中期势头强劲")
                                if "指数" in fund_type or "股票" in fund_type:
                                    reasons.append("中期趋势向上——但连续大涨后估值可能偏高，注意不要追在阶段性高点")
                                    if signal != "卖出":
                                        signal = "持有"
                                        tips.append("趋势好但已涨不少，此时加仓性价比降低，等回调再考虑")
                            elif ret_1m > 5:
                                reasons.append(f"近一月涨 {ret_1m:+.1f}%，中期温和上行")
                            elif ret_1m < -8:
                                reasons.append(f"近一月跌 {ret_1m:+.1f}%，中期明显走弱")
                                warnings.append("月度跌幅超8%需要重视——这不仅仅是短期噪音，可能是趋势性转变的信号")
                                if pnl_pct < -0.05:
                                    signal = "减仓"
                                    urgency += 2
                            elif ret_1m < -3:
                                reasons.append(f"近一月跌 {ret_1m:+.1f}%，中期偏弱")
                            else:
                                reasons.append(f"近一月变化 {ret_1m:+.1f}%，中期横盘整理")

                        # Weekly data as supplementary info
                        if nav_ok and ret_1w is not None:
                            if abs(ret_1w) < 2:
                                reasons.append(f"近一周 {ret_1w:+.1f}%（属正常波动，不作为决策依据）")
                            else:
                                reasons.append(f"近一周 {ret_1w:+.1f}%（周度参考，需结合月度趋势判断）")

                        # ---- 维度2: 趋势一致性（月线为主、周线为辅）----
                        if nav_ok and ret_1m is not None and ret_3m is not None:
                            if ret_1m > 3 and ret_3m > 8:
                                reasons.append("月线和季线趋势一致向上——处于健康的中期上升通道")
                                if signal == "持有" and urgency < 2:
                                    signal = "加仓"
                                    urgency += 1
                                tips.append("中期趋势向上时，月度级别的回调是加仓机会，不要被几天的下跌吓到")
                            elif ret_1m < -3 and ret_3m < -5:
                                warnings.append("月线和季线趋势一致向下——中期下降通道已形成")
                                if signal != "卖出":
                                    signal = "减仓"
                                    urgency += 2
                                tips.append("下降趋势中不要急于抄底，等月线走平或拐头再考虑。宁愿买贵一点，不要买在半山腰")
                            elif ret_1m > 3 and ret_3m < -3:
                                reasons.append("月线转好但季线仍偏弱——可能是中期筑底回升的初期")
                                tips.append("月线走好是积极信号，但季线修复需要时间。可小仓位试水，确认趋势再加仓")
                            elif ret_1m < -3 and ret_3m > 5:
                                reasons.append("月线回调但季线趋势良好——大概率是上升趋势中的正常调整")
                                tips.append("牛回头是好事不是坏事。只要季线趋势没破坏，月线级别的回调反而提供了更好的入场点")

                        # ---- 维度3: 盈亏与仓位管理 ----
                        if pnl_pct > 0.25:
                            reasons.append(f"浮盈 {pnl_pct*100:.1f}%，收益可观")
                            if "股票" in fund_type or "指数" in fund_type:
                                signal = "减仓"
                                urgency += 2
                                tips.append("盈利超25%时，贪婪是最大的敌人。建议分批止盈——先卖1/3锁定利润，余下让利润奔跑")
                        elif pnl_pct > 0.10:
                            reasons.append(f"浮盈 {pnl_pct*100:.1f}%，表现良好")
                            tips.append("已有不错的利润垫，心态会更从容。可以设定移动止盈线（如回撤5%就减仓），保护已有收益")
                        elif pnl_pct < -0.15:
                            warnings.append(f"浮亏 {pnl_pct*100:.1f}%，已触发15%止损线")
                            signal = "卖出"
                            urgency += 3
                            tips.append("止损是投资的第一课。亏损15%需要涨17.6%才能回本，亏损30%需要涨43%。截断亏损，让利润奔跑")
                        elif pnl_pct < -0.08:
                            reasons.append(f"浮亏 {pnl_pct*100:.1f}%，接近警戒线")
                            signal = "减仓"
                            urgency += 1
                            tips.append("亏损扩大时不要鸵鸟心态——正视亏损，评估是市场整体下跌还是基金本身出问题，区别对待")
                        elif pnl_pct < 0:
                            reasons.append(f"小幅浮亏 {pnl_pct*100:.1f}%，在正常波动范围内")

                        # ---- 维度4: 仓位集中度 ----
                        if weight > 0.30:
                            warnings.append(f"该基金占组合 {weight*100:.1f}%，过于集中。鸡蛋不要放在一个篮子里")
                            if signal == "加仓":
                                signal = "持有"
                                reasons.append("仓位已超30%，不建议继续加仓——分散是唯一免费的午餐")
                            urgency += 1
                        elif weight > 0.20:
                            reasons.append(f"仓位 {weight*100:.1f}%，占比偏高，注意控制")

                        # ---- 维度5: 基金类型特性 ----
                        if "债券" in fund_type:
                            if pnl_pct < -0.03:
                                warnings.append("债券基金亏损超3%极为罕见，可能持仓中有违约债券（踩雷），建议排查基金持仓")
                                signal = "卖出"
                                urgency += 3
                            elif pnl_pct < 0:
                                tips.append("债券基金短期小幅亏损通常是利率波动导致，不必过度反应。如果持有到期策略不变，净值会逐步修复")
                            else:
                                tips.append("债券基金是组合的压舱石，不要因为收益低就忽视它——熊市时它的稳定性价值才会体现")
                        elif "指数" in fund_type:
                            tips.append("指数基金的优势在于低费率和透明度。当前适合定投策略：越是下跌越要坚持买入，摊低成本等待估值回归")
                            if ret_1w is not None and ret_1w < -3:
                                tips.append("指数基金下跌时不要恐慌——你买的是国运和整个市场，而非某一家公司。只要经济长期向上，指数终会回来")
                        elif "混合" in fund_type:
                            tips.append("混合基金的优势在于基金经理可以灵活调仓。关注经理的选股能力和历史回撤控制，而非短期净值波动")
                        elif "QDII" in fund_type:
                            tips.append("QDII基金受汇率影响，人民币贬值利好QDII、升值则利空。关注汇率走势，当作额外的对冲维度")
                        elif "货币" in fund_type:
                            tips.append("货币基金是流动性管理工具，不是增值工具。这里的钱应该随时能取用，收益差距通常很小")

                        # ---- 维度6: 长期持有逻辑 ----
                        if ret_1y is not None and ret_1y > 20:
                            tips.append(f"该基金近一年收益 {ret_1y:+.1f}%，长期持有者已获利丰厚。好基金值得长期陪伴，时间是优秀资产的朋友")
                        elif ret_1y is not None and ret_1y < -20:
                            warnings.append(f"近一年跌幅 {ret_1y:+.1f}%，需要思考：是市场系统性下跌还是基金本身有问题？前者可等待，后者应果断换仓")

                        # ---- 综合决策（含时间权重）----
                        # Raw urgency-based signal
                        raw_signal = signal
                        if urgency >= 4:
                            raw_signal = "卖出"
                        elif urgency >= 3:
                            if signal not in ("卖出",):
                                raw_signal = "减仓"
                        elif urgency >= 2:
                            if signal == "持有":
                                raw_signal = "减仓"

                        # Don't override a strong sell with hold
                        if any("止损" in w or "踩雷" in w for w in warnings):
                            raw_signal = "卖出"

                        # ---- Time-perspective filter ----
                        # Downgrade urgency for short holding periods (new positions need time)
                        if holding_days is not None and holding_days < 30:
                            if raw_signal == "卖出":
                                raw_signal = "减仓"
                                tips.append("持有不足1个月，即使有问题也建议分步减仓而非一次性清仓")
                            elif raw_signal == "减仓":
                                raw_signal = "持有"
                                tips.append("持有不足1个月，短期波动属正常，建议至少观察1个月再决定")
                        elif holding_days is not None and holding_days < 90:
                            if raw_signal == "卖出" and "止损" not in str(warnings):
                                raw_signal = "减仓"
                                tips.append("持有不足3个月，建议减仓观察而非清仓。但如果触发止损线则按纪律执行")
                            elif raw_signal == "减仓" and urgency < 3:
                                raw_signal = "持有"
                                tips.append("持有不足3个月，轻微风险信号可先观察，不必急于操作")

                        signal = raw_signal

                        advice_list.append({
                            "code": code, "name": name, "shares": shares, "cost": cost,
                            "mkt_val": mkt_val, "weight": weight, "pnl_pct": pnl_pct,
                            "ret_1d": ret_1d, "ret_1w": ret_1w, "ret_1m": ret_1m,
                            "ret_3m": ret_3m, "ret_1y": ret_1y,
                            "signal": signal, "reasons": reasons, "warnings": warnings,
                            "tips": tips, "urgency": urgency,
                            "nav_ok": nav_ok, "fund_type": fund_type,
                        })

                    # Sort by urgency (most urgent first)
                    advice_list.sort(key=lambda x: x["urgency"], reverse=True)

                    # --- Display ---
                    st.markdown("---")
                    st.subheader("📋 持仓诊断报告")
                    st.caption("建议每月审视一次，不需要每天操作。短期波动3-5%是常态，保持耐心。")

                    # Summary stats
                    buy_count = sum(1 for a in advice_list if a["signal"] == "加仓")
                    sell_count = sum(1 for a in advice_list if a["signal"] == "卖出")
                    reduce_count = sum(1 for a in advice_list if a["signal"] == "减仓")
                    hold_count = sum(1 for a in advice_list if a["signal"] == "持有")

                    sc = st.columns(5)
                    sc[0].metric("总计持仓", f"{len(advice_list)}只")
                    sc[1].metric("可择机加仓", str(buy_count))
                    sc[2].metric("继续持有观察", str(hold_count))
                    sc[3].metric("可考虑减仓", str(reduce_count))
                    sc[4].metric("建议尽快处理", str(sell_count))

                    st.markdown("---")

                    # Action timeline reminder
                    urgent_alerts = [a for a in advice_list if a["urgency"] >= 3]
                    if urgent_alerts:
                        st.error(f"⚠ 有 {len(urgent_alerts)} 只基金需要重点关注，建议本周内处理")
                    mild_alerts = [a for a in advice_list if 1 <= a["urgency"] <= 2]
                    if mild_alerts:
                        st.warning(f"📋 有 {len(mild_alerts)} 只基金可列入观察名单，本月内审视即可")
                    stable = [a for a in advice_list if a["urgency"] <= 0]
                    if stable:
                        st.success(f"✅ {len(stable)} 只基金状态正常，按计划持有，无需操作")

                    st.markdown("---")

                    # Individual advice cards
                    for a in advice_list:
                        signal = a["signal"]
                        u = a["urgency"]
                        if signal == "卖出":
                            action_text = "建议尽快卖出"
                            action_time = "本周内处理"
                            icon = "🔴"
                        elif signal == "减仓":
                            action_text = "可考虑减仓"
                            action_time = "本月内处理"
                            icon = "🟡"
                        elif signal == "加仓":
                            action_text = "可择机加仓"
                            action_time = "本月内关注机会"
                            icon = "🔵"
                        else:
                            action_text = "继续持有"
                            action_time = "按计划持有"
                            icon = "⚪"

                        with st.container():
                            c1, c2, c3 = st.columns([3, 1, 1])
                            with c1:
                                st.markdown(f"### {icon} {a['name']}")
                                st.caption(f"代码: {a['code']} | 类型: {a['fund_type']} | 仓位: {a['weight']*100:.1f}%")
                            with c2:
                                st.metric("持仓盈亏", f"{a['pnl_pct']*100:+.1f}%")
                            with c3:
                                st.metric("操作建议", action_text)
                                st.caption(f"⏰ {action_time}")

                            # Performance data
                            if a["nav_ok"]:
                                rc = st.columns(4)
                                rc[0].metric("日涨跌", f"{a['ret_1d']:+.2f}%" if a['ret_1d'] is not None else "-")
                                rc[1].metric("近一周", f"{a['ret_1w']:+.2f}%" if a['ret_1w'] is not None else "-")
                                rc[2].metric("近一月", f"{a['ret_1m']:+.2f}%" if a['ret_1m'] is not None else "-")
                                rc[3].metric("近三月", f"{a['ret_3m']:+.2f}%" if a['ret_3m'] is not None else "-")
                            else:
                                st.caption("⚠ 未能获取净值走势数据，仅基于持仓盈亏分析")

                            # Analysis breakdown
                            with st.expander("📊 详细分析", expanded=(signal in ("卖出", "减仓"))):
                                st.markdown("**数据观察：**")
                                for r in a["reasons"]:
                                    st.caption(f"  📊 {r}")
                                if a["warnings"]:
                                    st.markdown("**⚠ 风险警示：**")
                                    for w in a["warnings"]:
                                        st.warning(w)
                                if a["tips"]:
                                    st.markdown("**💡 投资思考：**")
                                    for t in a["tips"]:
                                        st.info(t)

                            # Specific action with time context
                            if signal == "加仓":
                                suggested_add = a["mkt_val"] * 0.3
                                st.success(f"👉 {action_time}：建议加仓约 ¥{suggested_add:,.0f}（仓位30%），去「组合管理」→「添加买入」")
                            elif signal == "减仓":
                                suggested_sell = a["shares"] * 0.5
                                st.warning(f"👉 {action_time}：建议减仓约 {suggested_sell:,.0f} 份（仓位50%），去「组合管理」→「卖出减仓」")
                            elif signal == "卖出":
                                st.error(f"👉 {action_time}：建议全部卖出 {a['shares']:,.0f} 份，收回约 ¥{a['mkt_val']:,.0f}，去「组合管理」→「卖出减仓」")
                            elif signal == "持有":
                                st.info(f"👉 {action_time}，无需操作。继续持有，下个月再审视。")

                            st.markdown("---")

# ============================================================
# PAGE 6: Alert Center
# ============================================================
elif page == "⚠ 告警中心":
    st.title("告警中心")
    st.caption("实时风险监控和告警")

    from src.monitor.rules import ALL_RULES
    from src.monitor.alert_engine import AlertEngine
    from src.monitor.notifier import Notifier
    from src.portfolio.manager import PortfolioManager

    # Show configured rules
    st.subheader("已配置的告警规则")
    rule_cols = st.columns(3)
    for i, rule in enumerate(ALL_RULES):
        with rule_cols[i % 3]:
            sev_color = {"info": "blue", "warning": "orange", "critical": "red"}
            color = sev_color.get(rule.severity, "grey")
            st.markdown(f"🔔 **{rule.name}**")
            st.caption(f":{color}[{rule.severity.upper()}]")
            st.caption(rule.description)

    st.markdown("---")

    # Check alerts
    st.subheader("检查告警")
    col_a, col_b = st.columns([1, 3])
    with col_a:
        portfolios = repo.get_all_portfolios()
        p_options = {"全部组合": None}
        for p in portfolios:
            p_options[f"[{p.id}] {p.name}"] = p.id
        selected_scope = st.selectbox("检查范围", list(p_options.keys()))
        scope_pid = p_options[selected_scope]

    with col_b:
        if st.button("🔍 立即检查告警", use_container_width=True):
            with st.spinner("正在检查..."):
                engine = AlertEngine(repo)
                mgr = PortfolioManager(repo)

                if scope_pid:
                    summary = mgr.get_portfolio_summary(scope_pid)
                    context = AlertEngine.build_context(portfolio_summary=summary)
                    alerts = engine.check_and_persist(context, scope_pid)
                else:
                    alerts = []
                    for p in portfolios:
                        summary = mgr.get_portfolio_summary(p.id)
                        context = AlertEngine.build_context(portfolio_summary=summary)
                        alerts.extend(engine.check_and_persist(context, p.id))

                if alerts:
                    st.warning(f"触发 {len(alerts)} 条告警")
                    for alert in alerts:
                        sev = alert.get("severity", "info")
                        msg = alert.get("message", "")
                        if sev == "critical":
                            st.error(f"🔴 {msg}")
                        elif sev == "warning":
                            st.warning(f"🟡 {msg}")
                        else:
                            st.info(f"🔵 {msg}")
                        st.caption(f"时间: {alert.get('triggered_at', '')}")
                else:
                    st.success("✅ 未触发任何告警")

    # Alert history
    st.markdown("---")
    st.subheader("告警历史")
    recent_alerts = repo.get_alerts(limit=20)
    if recent_alerts:
        alert_data = []
        for a in recent_alerts:
            alert_data.append({
                "时间": str(a.triggered_at)[:19] if a.triggered_at else "",
                "级别": a.severity,
                "类型": a.alert_type,
                "消息": a.message,
                "状态": "已读" if a.is_read else "未读",
            })
        st.dataframe(pd.DataFrame(alert_data), use_container_width=True, hide_index=True)
    else:
        st.caption("暂无告警记录")
