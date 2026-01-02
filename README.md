# Portfolio Tracker: Top6_SL8_Hybrid Strategy

Production-ready portfolio tracking system using momentum-based stock selection with automated rebalancing and Telegram alerts.

## Strategy: Top6_SL8_Hybrid ✅

**Backtested Performance (2016-2026):**
```
CAGR:           35.38%
Sharpe Ratio:   4.51
Max Drawdown:   -13.13%
Holdings:       6 stocks (equal weight)
Stop-Loss:      -8%
Rebalance:      Weekly (Fridays)
Universe:       317 stocks (NIFTY 500)
```

**Momentum Formula:**
```
Score = 0.3×Return₁ₘ + 0.4×Return₃ₘ + 0.3×Return₆ₘ

Selection: Top 6 stocks by momentum score
Weighting: Equal weight per position (16.67% each)
Rebalancing: Weekly on Fridays
Risk Control: -8% stop-loss per position
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
Target CAGR:    35.38%
```

## Strategy Rules

✅ **Selection:** Top 6 stocks by 6-month momentum score  
✅ **Weight:** Equal 16.67% per position  
✅ **Stop-Loss:** Exit at -8% loss  
✅ **Rebalance:** Weekly on Fridays  
✅ **Trim:** Reduce if weight exceeds 20%  

## Performance Comparison

| Strategy | CAGR | Sharpe | MaxDD | Status |
|----------|------|--------|-------|--------|
| **Top6_SL8_Hybrid** | 35.38% | 4.51 | -13.13% | ✅ Optimal |
| Top7_SL9 | 34.98% | 4.69 | -13.32% | Close |
| Top5_SL8 | 32.25% | 4.18 | -14.30% | Lower |
| 8-Signal Multi-Factor | 27.92% | 1.56 | -99.93% | Worse |

## Weekly Checklist

- [ ] Friday: `python portfolio_tool.py`
- [ ] Review recommendations
- [ ] `python alert_runner.py` 
- [ ] Execute trades
- [ ] Check -8% stop-losses
- [ ] Verify position weights < 20%

## Configuration

Edit in `portfolio_tool.py`:
```python
STOP_LOSS_PCT = -8.0          # Exit threshold
TOP_N_PICKS = 6               # Select top 6
MAX_WEIGHT = 0.20             # Weight cap
MOMENTUM_WEIGHTS = {
    '1m': 0.3,
    '3m': 0.4,
    '6m': 0.3
}
```

---

**Status:** ✅ Production Ready | **Last Updated:** Jan 3, 2026
- If a name is unlisted or a ticker is unavailable, set `ticker: null` and `manual_price` to the latest price to keep PnL current.
- Recommendations are heuristic and should be double-checked against your own risk rules and taxes.
