#!/usr/bin/env python3
"""Monthly SIP engine per fundamentals-first spec."""
import argparse
import datetime as dt
import yaml
from pathlib import Path

from nifty500_universe import NIFTY500_TICKERS
from data.fundamentals_loader import load_fundamentals_csv
from data.mock_data import load_mock_fundamentals, load_mock_trends
from data.prices_loader import fetch_trend_inputs, fetch_nifty_inputs
from engine.fundamental_engine import screen_and_score, apply_sector_constraints
from engine.trend_engine import evaluate_trends
from engine.regime_filter import market_regime_is_cautious
from engine.sip_allocator import allocate_sip
from reporting.monthly_report import render_report, save_report


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run(cfg_path: str) -> str:
    cfg = load_config(cfg_path)

    data_cfg = cfg.get("data", {})
    fundamentals_csv = Path(data_cfg.get("fundamentals_csv", "data/fundamentals.csv"))

    if fundamentals_csv.exists():
        fundamentals = load_fundamentals_csv(fundamentals_csv, NIFTY500_TICKERS)
    else:
        fundamentals = load_mock_fundamentals()

    price_lookback = int(data_cfg.get("price_lookback_days", 260))
    trend_inputs = fetch_trend_inputs([f.ticker for f in fundamentals], days=price_lookback)

    picks = screen_and_score(fundamentals, cfg)
    picks = apply_sector_constraints(picks, cfg)

    trends = evaluate_trends(trend_inputs, cfg)
    nifty_symbol = data_cfg.get("nifty_symbol", "^NSEI")
    nifty_inputs = fetch_nifty_inputs(nifty_symbol, days=price_lookback)
    regime_cautious = market_regime_is_cautious(nifty_inputs, cfg) if nifty_inputs else False

    actions = allocate_sip(picks, trends, cfg, regime_cautious)
    report = render_report(actions, regime_cautious)
    saved = save_report(report, cfg)
    return f"Saved report to {saved}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Long-term SIP engine")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    args = parser.parse_args()
    result = run(args.config)
    print(result)


if __name__ == "__main__":
    main()
