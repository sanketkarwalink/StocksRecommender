# Portfolio Tracker (India)

Python script to track holdings, fetch quotes (via yfinance), and suggest basic actions (hold/trim/sell) based on stop-loss, take-profit, and weight caps.

## Setup

1) Install deps:
```
pip install -r requirements.txt
```
2) Update holdings in `data/holdings.yaml`.
3) Run:
```
python portfolio_tool.py
```

Backtest the broader momentum-vol strategy (monthly by default, last 5–6 years):
```
python strategy_backtest.py
```
Options: `--start YYYY-MM-DD`, `--end YYYY-MM-DD`, `--top N` (picks per rebalance), `--volcap` (vol filter), `--freq` (e.g., `M` monthly, `W-FRI` weekly).

## Config knobs (edit in `portfolio_tool.py`)
- `STOP_LOSS_PCT`: sell if drawdown crosses this (default -15%).
- `TAKE_PROFIT_PCT`: trim when gains exceed this and weight is high (default 35%).
- `MAX_WEIGHT`: maximum allowed position weight (default 25%).
- `REBALANCE_BAND`: tolerance band before trimming for weight (default 5%).

## Notes
- NSE tickers use the `.NS` suffix (e.g., `INFY.NS`, `SBIN.NS`, `ITC.NS`). Adjust any tickers that fail to fetch.
- If a name is unlisted or a ticker is unavailable, set `ticker: null` and `manual_price` to the latest price to keep PnL current.
- Recommendations are heuristic and should be double-checked against your own risk rules and taxes.
