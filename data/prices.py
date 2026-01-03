from dataclasses import dataclass
from typing import Optional


@dataclass
class TrendInputs:
    price: float
    sma50: float
    sma200: float
    return_3m: float
    return_6m: float
    rsi14: float
    vol20: Optional[float] = None


class TrendState:
    ACCUMULATE = "ACCUMULATE"
    NEUTRAL = "NEUTRAL"
    PAUSE = "PAUSE"


def determine_trend_state(ti: TrendInputs, cfg: dict) -> str:
    rsi_low = cfg["trend"]["rsi_low"]
    rsi_high = cfg["trend"]["rsi_high"]
    min_r3 = cfg["trend"]["min_return_3m"]
    min_r6 = cfg["trend"]["min_return_6m"]

    if ti.price > ti.sma200 and ti.return_3m >= min_r3 and ti.return_6m >= min_r6 and rsi_low <= ti.rsi14 <= rsi_high:
        return TrendState.ACCUMULATE
    if ti.price < ti.sma200 and ti.return_6m < 0:
        return TrendState.PAUSE
    if ti.price >= ti.sma200 * 0.9:
        return TrendState.NEUTRAL
    return TrendState.NEUTRAL
