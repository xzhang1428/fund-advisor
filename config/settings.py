"""Central configuration for the fund advisory system."""

from pathlib import Path
from enum import Enum

# ============================================================
# Paths
# ============================================================
import os
PROJECT_ROOT = Path(__file__).parent.parent

# Use /tmp for DB on Streamlit Cloud (Linux), local dir on Windows
if os.environ.get('STREAMLIT_CLOUD') or os.environ.get('IS_STREAMLIT_CLOUD'):
    DATA_DIR = Path('/tmp/fund_advisor_data')
else:
    DATA_DIR = PROJECT_ROOT / "data"

DB_PATH = DATA_DIR / "fund_advisory.db"
CACHE_DIR = DATA_DIR / "cache"

# Ensure directories exist
try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

# Database
DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

# ============================================================
# Enums
# ============================================================
class FundCategory(str, Enum):
    STOCK = "股票型"
    MIXED = "混合型"
    BOND = "债券型"
    INDEX = "指数型"
    MONEY = "货币型"
    QDII = "QDII"

class RiskProfile(str, Enum):
    CONSERVATIVE = "保守型"
    MODERATE = "稳健型"
    BALANCED = "平衡型"
    AGGRESSIVE = "进取型"

class MarketRegime(str, Enum):
    BULL = "牛市"
    BEAR = "熊市"
    SIDEWAYS = "震荡"

class Signal(str, Enum):
    BUY = "买入"
    SELL = "卖出"
    HOLD = "持有"
    ACCUMULATE = "加仓"
    REDUCE = "减仓"

# ============================================================
# Market Indices to track
# ============================================================
TRACKED_INDICES = {
    "000001": "上证指数",
    "399001": "深证成指",
    "000300": "沪深300",
    "000905": "中证500",
    "399006": "创业板指",
    "000688": "科创50",
}

# ============================================================
# Scoring weights (per category)
# ============================================================
SCORING_WEIGHTS = {
    "default": {
        "return_score": 0.35,
        "sharpe_score": 0.15,
        "drawdown_score": 0.15,
        "manager_score": 0.10,
        "fee_score": 0.05,
        "size_score": 0.05,
        "market_fit_score": 0.15,
    },
    "指数型": {
        "return_score": 0.20,
        "sharpe_score": 0.10,
        "drawdown_score": 0.10,
        "tracking_error_score": 0.15,
        "fee_score": 0.20,
        "size_score": 0.10,
        "valuation_score": 0.15,
    },
    "债券型": {
        "return_score": 0.25,
        "sharpe_score": 0.10,
        "drawdown_score": 0.25,
        "manager_score": 0.10,
        "fee_score": 0.15,
        "size_score": 0.10,
        "market_fit_score": 0.05,
    },
    "货币型": {
        "return_score": 0.50,
        "sharpe_score": 0.05,
        "drawdown_score": 0.10,
        "fee_score": 0.25,
        "size_score": 0.05,
        "market_fit_score": 0.05,
    },
}

# ============================================================
# Risk profile allocation templates
# ============================================================
RISK_ALLOCATIONS = {
    "保守型": {"货币型": 0.40, "债券型": 0.35, "混合型": 0.15, "指数型": 0.07, "股票型": 0.03, "QDII": 0.00},
    "稳健型": {"货币型": 0.15, "债券型": 0.25, "混合型": 0.25, "指数型": 0.20, "股票型": 0.10, "QDII": 0.05},
    "平衡型": {"货币型": 0.08, "债券型": 0.15, "混合型": 0.25, "指数型": 0.25, "股票型": 0.20, "QDII": 0.07},
    "进取型": {"货币型": 0.03, "债券型": 0.08, "混合型": 0.20, "指数型": 0.30, "股票型": 0.30, "QDII": 0.09},
}

# ============================================================
# Alert thresholds
# ============================================================
ALERT_THRESHOLDS = {
    "single_fund_max_drawdown": 0.10,
    "portfolio_max_drawdown": 0.15,
    "pe_percentile_high": 0.80,
    "pe_percentile_low": 0.20,
    "manager_change_days": 90,
}

# ============================================================
# Fetch settings
# ============================================================
CACHE_TTL_HOURS = 4
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = [5, 15, 60]
REQUEST_TIMEOUT = 30

# ============================================================
# Analysis settings
# ============================================================
RISK_FREE_RATE = 0.03          # 3% annual (China 1Y government bond approx)
LOOKBACK_YEARS = 5             # for PE/PB percentile
REBALANCE_THRESHOLD = 0.05     # 5% drift triggers rebalance suggestion
ANNUAL_TRADING_DAYS = 242      # Chinese market trading days per year

# ============================================================
# Fund category mapping (from akshare fund types)
# ============================================================
FUND_TYPE_MAPPING = {
    "股票型": "股票型",
    "混合型": "混合型",
    "债券型": "债券型",
    "指数型": "指数型",
    "货币型": "货币型",
    "QDII": "QDII",
    "股票指数": "指数型",
    "增强指数型": "指数型",
    "偏股混合型": "混合型",
    "偏债混合型": "混合型",
    "灵活配置型": "混合型",
    "短期纯债型": "债券型",
    "中长期纯债型": "债券型",
    "混合债券型": "债券型",
    "被动指数型": "指数型",
    "商品型": "QDII",
}
