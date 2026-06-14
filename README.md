# Fund Advisory System - Chinese Fund Investment Advisor

A comprehensive Chinese-market fund investment advisory system with market analysis, portfolio management, fund recommendations, and real-time monitoring.

## Features

- **Market Data**: Fetch real-time Chinese market index data (SSE, CSI 300, CSI 500, ChiNext, STAR 50)
- **Fund Analysis**: Multi-factor scoring (returns, Sharpe ratio, drawdown, manager quality, fees)
- **Technical Analysis**: MACD, RSI, KDJ, Bollinger Bands, moving average crossover signals
- **Market Regime Detection**: Bull/Bear/Sideways market classification
- **Valuation Analysis**: PE/PB percentile analysis for timing
- **Portfolio Management**: Create portfolios, track holdings, P&L, allocation
- **Fund Recommendations**: Smart fund recommendations based on scores and market conditions
- **Trading Signals**: Buy/Sell/Hold/Accumulate/Reduce signals with confidence levels
- **Asset Allocation**: Mean-Variance Optimization and Risk Parity
- **Alert Monitoring**: Configurable alerts for drawdown, manager changes, valuation extremes
- **CLI Interface**: Rich command-line interface
- **Web Dashboard**: Streamlit dashboard with interactive charts

## Quick Start

### Installation

```bash
pip install -r requirements.txt
python scripts/init_db.py
```

### Fetch Data

```bash
# Fetch all data (market indices, funds, macro)
python -m src.cli.main fetch all

# Or fetch specific data
python -m src.cli.main fetch market
python -m src.cli.main fetch funds
python -m src.cli.main fetch macro

# Backfill 3+ years of historical data
python scripts/backfill_data.py
```

### Create Portfolio

```bash
# Create a new portfolio
python -m src.cli.main portfolio create \
  --name "My Retirement Fund" \
  --capital 100000 \
  --profile Moderate

# Add holdings
python -m src.cli.main portfolio add 1 \
  --fund 000001 \
  --shares 10000 \
  --cost 1.5000
```

### Market Analysis

```bash
# Market diagnostic
python -m src.cli.main analyze market

# Deep fund analysis
python -m src.cli.main analyze fund 000001

# Valuation analysis
python -m src.cli.main analyze valuation

# Sector performance
python -m src.cli.main analyze sector
```

### Recommendations

```bash
# Get top fund recommendations
python -m src.cli.main recommend funds --category Mixed --top 10

# Generate trading signals for your portfolio
python -m src.cli.main recommend portfolio 1

# Asset allocation advice
python -m src.cli.main recommend allocation --profile Moderate
```

### Monitoring

```bash
# Check alerts
python -m src.cli.main monitor check

# Continuous monitoring
python -m src.cli.main monitor watch --interval 300

# List alert rules
python -m src.cli.main monitor rules
```

### Risk Assessment

```bash
# Take the risk tolerance questionnaire
python -m src.cli.main risk-assessment
```

### Web Dashboard

```bash
streamlit run dashboard/app.py
```

## Project Structure

```
fund-advisory-system/
├── config/                  # Configuration and settings
│   ├── settings.py          # All constants, weights, thresholds
│   └── fund_categories.yaml # Fund category definitions
├── src/
│   ├── fetcher/             # Data fetching (akshare API)
│   ├── storage/             # SQLAlchemy ORM + SQLite
│   ├── analysis/            # Technical/fundamental analysis
│   ├── recommendation/      # Scoring, allocation, signals
│   ├── portfolio/           # Portfolio management
│   ├── monitor/             # Alert system
│   └── cli/                 # CLI commands
├── dashboard/               # Streamlit web UI
├── scripts/                 # Utility scripts
│   ├── init_db.py           # Database setup
│   ├── backfill_data.py     # Historical data loader
│   └── scheduled_update.py  # Daily update cron
└── data/                    # SQLite DB + cache
```

## Architecture

```
akshare API → Fetcher → SQLite DB → Analysis Engine
                                      ↓
                                 Recommendation Engine
                                      ↓
                    ┌─────────────────┼─────────────────┐
                    ↓                 ↓                   ↓
              Portfolio Mgr     Signal Generator    CLI/Dashboard
                    ↓
              Alert Monitor
```

## Scoring Model

Each fund receives a 0-100 composite score based on:

| Factor | Weight | Description |
|---|---|---|
| 1Y Return | 20% | Recent performance |
| 3Y Return | 15% | Long-term track record |
| Sharpe Ratio | 15% | Risk-adjusted returns |
| Max Drawdown | 15% | Downside protection (inverted) |
| Manager Quality | 10% | Manager experience/tenure |
| Fee Efficiency | 5% | Management fees |
| Size Fit | 5% | AUM appropriateness |
| Market Fit | 15% | Category alignment with regime |

Weights are adjusted based on market regime (bull/bear/sideways).

## Signal Logic

```
Score >= 70 + Bull Market for Equity → BUY
Score >= 70 + Undervalued Index → BUY
Score >= 70 → ACCUMULATE
Score 50-70 → HOLD
Score 30-50 + In Holdings → REDUCE
Score < 30 + In Holdings → SELL
Stop-loss (>15% loss) → SELL (override)
```

## Risk Profiles

| Profile | Money | Bond | Mixed | Index | Stock | QDII |
|---|---|---|---|---|---|---|
| Conservative | 40% | 35% | 15% | 7% | 3% | 0% |
| Moderate | 15% | 25% | 25% | 20% | 10% | 5% |
| Balanced | 8% | 15% | 25% | 25% | 20% | 7% |
| Aggressive | 3% | 8% | 20% | 30% | 30% | 9% |

## Data Sources

- Market indices: akshare (东方财富/sina)
- Fund NAV & rankings: akshare (天天基金/东方财富)
- Macro indicators: akshare (National Bureau of Statistics)
- Sector data: akshare (东方财富行业板块)

## Requirements

- Python 3.12+
- SQLite 3
- packages: akshare, pandas, numpy, scipy, SQLAlchemy, pydantic, scikit-learn, matplotlib, streamlit, plotly, click, rich, tabulate

## License

MIT
