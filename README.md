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
