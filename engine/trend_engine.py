from dataclasses import dataclass
from typing import Dict

from data.prices import TrendInputs, determine_trend_state


@dataclass
class TrendSignal:
    ticker: str
    state: str
    inputs: TrendInputs


def evaluate_trends(trend_map: Dict[str, TrendInputs], cfg: dict) -> Dict[str, TrendSignal]:
    results: Dict[str, TrendSignal] = {}
    for ticker, ti in trend_map.items():
        state = determine_trend_state(ti, cfg)
        results[ticker] = TrendSignal(ticker=ticker, state=state, inputs=ti)
    return results
