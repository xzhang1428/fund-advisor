"""SQLAlchemy ORM models for the fund advisory system."""

from datetime import date, datetime
from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime, Text,
    Boolean, ForeignKey, UniqueConstraint, Index, create_engine
)
from sqlalchemy.orm import DeclarativeBase, relationship
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class Base(DeclarativeBase):
    pass


# ============================================================
# Market Indices
# ============================================================
class MarketIndex(Base):
    __tablename__ = "market_indices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, comment="指数代码, e.g., '000001' (上证)")
    index_name = Column(String(50), nullable=False, comment="指数名称")
    trade_date = Column(Date, nullable=False, comment="交易日期")
    open = Column(Float, comment="开盘价")
    high = Column(Float, comment="最高价")
    low = Column(Float, comment="最低价")
    close = Column(Float, comment="收盘价")
    volume = Column(Float, comment="成交量(手)")
    amount = Column(Float, comment="成交额(元)")
    pe_ttm = Column(Float, comment="PE-TTM")
    pb = Column(Float, comment="PB")
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint("symbol", "trade_date", name="uq_idx_symbol_date"),
        Index("idx_indices_date", "trade_date"),
        Index("idx_indices_symbol", "symbol"),
    )


# ============================================================
# Fund Basic Info
# ============================================================
class FundBasicInfo(Base):
    __tablename__ = "fund_basic_info"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fund_code = Column(String(6), unique=True, nullable=False, comment="基金代码")
    fund_name = Column(String(100), nullable=False, comment="基金名称")
    fund_type = Column(String(20), nullable=False, comment="基金类型")
    management_company = Column(String(100), comment="基金公司")
    manager_name = Column(String(50), comment="基金经理")
    manager_start_date = Column(Date, comment="基金经理任职日期")
    inception_date = Column(Date, comment="成立日期")
    aum_yuan = Column(Float, comment="基金规模(亿元)")
    management_fee_pct = Column(Float, comment="管理费率")
    custodian_fee_pct = Column(Float, comment="托管费率")
    benchmark_index = Column(String(50), comment="业绩基准")
    investment_style = Column(String(50), comment="投资风格")
    is_etf = Column(Boolean, default=False, comment="是否ETF")
    can_buy = Column(Boolean, default=True, comment="是否可申购")
    risk_level = Column(String(20), comment="风险等级")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# ============================================================
# Fund NAV
# ============================================================
class FundNav(Base):
    __tablename__ = "fund_nav"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fund_code = Column(String(6), nullable=False, comment="基金代码")
    trade_date = Column(Date, nullable=False, comment="交易日期")
    nav = Column(Float, nullable=False, comment="单位净值")
    accumulated_nav = Column(Float, comment="累计净值")
    daily_return = Column(Float, comment="日涨跌幅(%)")
    subscription_status = Column(String(10), comment="申购状态")
    redemption_status = Column(String(10), comment="赎回状态")
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint("fund_code", "trade_date", name="uq_nav_code_date"),
        Index("idx_nav_code", "fund_code"),
        Index("idx_nav_date", "trade_date"),
    )


# ============================================================
# Fund Performance (computed metrics)
# ============================================================
class FundPerformance(Base):
    __tablename__ = "fund_performance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fund_code = Column(String(6), nullable=False, comment="基金代码")
    calc_date = Column(Date, nullable=False, comment="计算日期")
    return_1w = Column(Float, comment="近1周收益率")
    return_1m = Column(Float, comment="近1月收益率")
    return_3m = Column(Float, comment="近3月收益率")
    return_6m = Column(Float, comment="近6月收益率")
    return_1y = Column(Float, comment="近1年收益率")
    return_3y = Column(Float, comment="近3年收益率")
    return_ytd = Column(Float, comment="今年以来收益率")
    annualized_return_3y = Column(Float, comment="3年年化收益率")
    sharpe_ratio_1y = Column(Float, comment="1年夏普比率")
    sharpe_ratio_3y = Column(Float, comment="3年夏普比率")
    max_drawdown_1y = Column(Float, comment="1年最大回撤")
    max_drawdown_3y = Column(Float, comment="3年最大回撤")
    volatility_1y = Column(Float, comment="1年年化波动率")
    volatility_3y = Column(Float, comment="3年年化波动率")
    calmar_ratio = Column(Float, comment="卡玛比率")
    information_ratio = Column(Float, comment="信息比率")
    tracking_error = Column(Float, comment="跟踪误差")
    alpha = Column(Float, comment="Alpha")
    beta = Column(Float, comment="Beta")
    updated_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint("fund_code", "calc_date", name="uq_perf_code_date"),
    )


# ============================================================
# Fund Scores
# ============================================================
class FundScore(Base):
    __tablename__ = "fund_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fund_code = Column(String(6), nullable=False, comment="基金代码")
    calc_date = Column(Date, nullable=False, comment="计算日期")
    total_score = Column(Float, comment="综合得分(0-100)")
    return_score = Column(Float, comment="收益得分")
    sharpe_score = Column(Float, comment="夏普得分")
    drawdown_score = Column(Float, comment="回撤得分")
    manager_score = Column(Float, comment="基金经理得分")
    fee_score = Column(Float, comment="费率得分")
    size_score = Column(Float, comment="规模得分")
    market_fit_score = Column(Float, comment="市场适配得分")
    percentile_in_category = Column(Float, comment="同类排名百分位")
    signal = Column(String(10), comment="交易信号: 买入/持有/卖出/加仓/减仓")
    updated_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint("fund_code", "calc_date", name="uq_score_code_date"),
    )


# ============================================================
# Sector Performance
# ============================================================
class SectorPerformance(Base):
    __tablename__ = "sector_performance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sector_code = Column(String(20), nullable=False, comment="申万行业代码")
    sector_name = Column(String(50), nullable=False, comment="行业名称")
    trade_date = Column(Date, nullable=False, comment="交易日期")
    return_1d = Column(Float, comment="日涨跌幅")
    return_1w = Column(Float, comment="周涨跌幅")
    return_1m = Column(Float, comment="月涨跌幅")
    return_ytd = Column(Float, comment="今年以来涨跌幅")
    pe_ttm = Column(Float, comment="PE-TTM")
    pb = Column(Float, comment="PB")
    volume = Column(Float, comment="成交量")
    main_inflow = Column(Float, comment="主力资金净流入")
    updated_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint("sector_code", "trade_date", name="uq_sector_code_date"),
    )


# ============================================================
# Macro Indicators
# ============================================================
class MacroIndicator(Base):
    __tablename__ = "macro_indicators"

    id = Column(Integer, primary_key=True, autoincrement=True)
    indicator_type = Column(String(30), nullable=False, comment="指标类型: CPI/PMI/SHIBOR/M2/GDP")
    period = Column(String(20), comment="时间周期")
    value = Column(Float, nullable=False, comment="指标值")
    yoy_change = Column(Float, comment="同比变化")
    mom_change = Column(Float, comment="环比变化")
    updated_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint("indicator_type", "period", name="uq_macro_type_period"),
    )


# ============================================================
# Portfolio
# ============================================================
class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="组合名称")
    initial_capital = Column(Float, nullable=False, comment="初始资金")
    risk_profile = Column(String(20), nullable=False, comment="风险偏好")
    created_at = Column(Date, nullable=False, comment="创建日期")
    description = Column(Text, comment="描述")
    is_active = Column(Boolean, default=True, comment="是否活跃")

    holdings = relationship("Holding", back_populates="portfolio", cascade="all, delete-orphan")
    allocations = relationship("AllocationPlan", back_populates="portfolio", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="portfolio", cascade="all, delete-orphan")


# ============================================================
# Allocation Plan
# ============================================================
class AllocationPlan(Base):
    __tablename__ = "allocation_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    category = Column(String(20), nullable=False, comment="基金类型")
    target_weight = Column(Float, nullable=False, comment="目标权重")
    max_weight = Column(Float, comment="最大权重")
    min_weight = Column(Float, comment="最小权重")

    portfolio = relationship("Portfolio", back_populates="allocations")

    __table_args__ = (
        UniqueConstraint("portfolio_id", "category", name="uq_alloc_portfolio_cat"),
    )


# ============================================================
# Holding
# ============================================================
class Holding(Base):
    __tablename__ = "holdings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    fund_code = Column(String(6), nullable=False, comment="基金代码")
    shares = Column(Float, nullable=False, comment="持有份额")
    avg_cost = Column(Float, nullable=False, comment="持仓成本(每份)")
    purchase_date = Column(Date, nullable=False, comment="首次购买日期")
    last_nav = Column(Float, comment="最新净值")
    last_update_date = Column(Date, comment="最新更新日期")
    notes = Column(Text, comment="备注")

    portfolio = relationship("Portfolio", back_populates="holdings")

    __table_args__ = (
        UniqueConstraint("portfolio_id", "fund_code", name="uq_holding_portfolio_fund"),
    )


# ============================================================
# Transaction
# ============================================================
class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    fund_code = Column(String(6), nullable=False, comment="基金代码")
    transaction_type = Column(String(10), nullable=False, comment="BUY/SELL/DIVIDEND")
    transaction_date = Column(Date, nullable=False, comment="交易日期")
    shares = Column(Float, nullable=False, comment="份额")
    price = Column(Float, nullable=False, comment="成交净值")
    amount = Column(Float, nullable=False, comment="成交金额")
    fee = Column(Float, comment="手续费")
    notes = Column(Text, comment="备注")

    portfolio = relationship("Portfolio", back_populates="transactions")


# ============================================================
# Alert
# ============================================================
class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, comment="关联组合ID")
    fund_code = Column(String(6), comment="关联基金代码")
    alert_type = Column(String(50), nullable=False, comment="告警类型")
    severity = Column(String(20), nullable=False, comment="严重程度: info/warning/critical")
    message = Column(Text, nullable=False, comment="告警消息")
    is_read = Column(Boolean, default=False, comment="是否已读")
    triggered_at = Column(DateTime, default=datetime.now, comment="触发时间")


# ============================================================
# Daily Snapshot (portfolio value tracker)
# ============================================================
class DailySnapshot(Base):
    __tablename__ = "daily_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    snapshot_date = Column(Date, nullable=False, comment="日期")
    total_value = Column(Float, comment="当日总市值")
    daily_pnl = Column(Float, comment="当日盈亏金额")
    daily_return_pct = Column(Float, comment="当日收益率")
    notes = Column(Text, comment="备注（如分红、加仓等）")

    __table_args__ = (
        UniqueConstraint("portfolio_id", "snapshot_date", name="uq_snapshot_portfolio_date"),
    )
