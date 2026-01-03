#!/usr/bin/env python3
"""Monthly SIP engine per fundamentals-first spec."""
import argparse
import datetime as dt
import yaml

from data.mock_data import load_mock_fundamentals, load_mock_trends
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

    fundamentals = load_mock_fundamentals()
    trend_inputs = load_mock_trends()

    picks = screen_and_score(fundamentals, cfg)
    picks = apply_sector_constraints(picks, cfg)

    trends = evaluate_trends({k: v for k, v in trend_inputs.items() if k != "NIFTY50"}, cfg)
    nifty = trend_inputs.get("NIFTY50")
    regime_cautious = market_regime_is_cautious(nifty, cfg) if nifty else False

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
