# Portfolio Tracker: Top6_SL10 Strategy

Production-ready portfolio tracking system using momentum-based stock selection with automated rebalancing and Telegram alerts.

## Strategy: Top6_SL10 ✅

**Backtested Performance (2016-2026):**
```
CAGR:           34.33%
Sharpe Ratio:   4.49
Max Drawdown:   -13.27%
Holdings:       6 stocks (equal weight, ~16.7% each)
Stop-Loss:      -10%
Rebalance:      Weekly (Fridays)
Universe:       251 stocks (NIFTY 500, filtered for data quality)
```

**Momentum Formula:**
```
Score = 0.3×Return₁ₘ + 0.4×Return₃ₘ + 0.3×Return₆ₘ

Selection: Top 6 stocks by momentum score
Weighting: Equal weight per position (~16.7% each)
Rebalancing: Weekly on Fridays
Risk Control: -10% stop-loss per position; 20% soft max weight / 18% hard cap
```

## Quick Start

1. **Install dependencies:**
```bash
python -m venv .venv
source .venv/bin/activate
pip install pandas yfinance python-telegram-bot
```

2. **Generate recommendations:**
```bash
python portfolio_tool.py
```

3. **Send alerts:**
```bash
python alert_runner.py
```

4. **Validate performance:**
```bash
python optimize_strategy.py
```

## Core Files

- **portfolio_tool.py** - Live portfolio analysis & recommendations
- **alert_runner.py** - Telegram notifications
- **optimize_strategy.py** - Backtest validation
- **nifty500_universe.py** - 317-stock screening universe
- **test_improvements.py** - Parameter testing

## Current Portfolio

```
Value:          ₹52,087
Holdings:       8 stocks
PnL:            +₹4,272 (+8.93%)
Target CAGR:    34.33%
```

## Strategy Rules

✅ **Selection:** Top 6 stocks by blended 1m/3m/6m momentum score  
✅ **Weight:** Equal ~16.7% per position  
✅ **Stop-Loss:** Exit at -10% loss  
✅ **Rebalance:** Weekly on Fridays  
✅ **Trim:** Reduce if weight exceeds 20% (hard cap 18%)  

## Performance Comparison

| Strategy | CAGR | Sharpe | MaxDD | Status |
|----------|------|--------|-------|--------|
| **Top6_SL10** | 34.33% | 4.49 | -13.27% | ✅ Default (best CAGR) |
| Dynamic_SL10 (8 stocks) | 31.97% | 4.70 | -15.36% | Best Sharpe |
| Tighter_SL_8 (8 stocks) | 33.29% | 4.66 | -12.89% | Best MaxDD |
| Top10_SL10 | 30.73% | 4.47 | -17.38% | Diversified |

## Weekly Checklist

- [ ] Friday: `python portfolio_tool.py`
- [ ] Review recommendations
- [ ] `python alert_runner.py` 
- [ ] Execute trades
- [ ] Check -10% stop-losses
- [ ] Verify position weights < 20%

## Configuration

Defaults (Top6_SL10) in `portfolio_tool.py`:
```python
STOP_LOSS_PCT = -10.0
TAKE_PROFIT_PCT = 40.0
TOP_N_PICKS = 6
MAX_WEIGHT = 0.20
HARD_CAP_WEIGHT = 0.18
MOMENTUM_WEIGHTS = (0.3, 0.4, 0.3)
VOL_CAP = 40.0
```

CLI overrides (example):
```
python portfolio_tool.py \
    --top-n 6 --stop-loss -10 --take-profit 40 \
    --max-weight 0.20 --hard-cap-weight 0.18 --rebalance-band 0.03 \
    --vol-cap 40 --momentum-weights 0.3,0.4,0.3
```

---

**Status:** ✅ Production Ready | **Last Updated:** Jan 3, 2026
- If a name is unlisted or a ticker is unavailable, set `ticker: null` and `manual_price` to the latest price to keep PnL current.
- Recommendations are heuristic and should be double-checked against your own risk rules and taxes.

---

# Long-Term SIP Engine (Fundamentals-First)

This module builds a long-term SIP portfolio using quarterly fundamentals for inclusion and monthly trend signals only to pace SIP amounts. No stop-losses or frequent trading.

**How it works**
- Universe: NIFTY 500 filtered (mcap > ₹3,000 Cr, listed >3y, ADV > ₹5 Cr)
- Fundamentals (quarterly): hard filters on ROCE ≥15%, D/E ≤0.6, positive 3Y FCF, Sales CAGR 5Y ≥8%, Promoter holding ≥45%; score ≥65 using weighted mix of ROCE, growth, leverage, FCF, promoter stability
- Valuation tag: UNDERVALUED / FAIR / OVERVALUED (PE vs sector, PEG, PB) influences SIP size
- Trend (monthly): 200DMA + 3m/6m returns + RSI 40–65 -> ACCUMULATE / NEUTRAL / PAUSE; no exits
- Regime: if NIFTY50 below 200DMA, reduce all SIPs by 40% (no sells)
- Constraints: 12–18 stocks, max stock weight 12%, max sector 25%, max 2 per sector unless score >80

**Outputs**
- Monthly SIP report with score, valuation tag, trend state, SIP action and recommended amount
- Optional alerts (to be wired) for SIP pause/resume or fundamentals drop

**Run (uses mock data placeholder)**
```
python monthly_sip.py --config config.yaml
```
Report saves to `reports/`.

**Real data setup**
- Provide `data/fundamentals.csv` with columns:
    `ticker,name,sector,market_cap_cr,listing_years,adv_cr,roce,debt_to_equity,sales_cagr_5y,profit_cagr_5y,fcf_3y_positive,promoter_holding,promoter_change_pct,pe,pb,peg,sector_pe_median`
- Tickers should match `nifty500_universe.py` tickers. CSV is filtered to NIFTY500 and hard rules.
- Prices and trend signals pull from Yahoo Finance via `yfinance` using the filtered tickers; NIFTY50 regime uses symbol from config (default `^NSEI`).

If `data/fundamentals.csv` is missing, the pipeline falls back to mock data for demonstration only.
