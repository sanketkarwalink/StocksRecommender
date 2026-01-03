from dataclasses import dataclass
from typing import Dict, List

from engine.fundamental_engine import FundamentalPick
from engine.trend_engine import TrendSignal
from data.valuations import ValuationTag


@dataclass
class SIPAction:
    ticker: str
    name: str
    sector: str
    fundamental_score: float
    valuation: str
    trend_state: str
    allocation_multiplier: float
    recommended_sip: float
    notes: str


def _multiplier(valuation: ValuationTag, trend_state: str, cfg: dict) -> float:
    mult_cfg = cfg["sip"]["multipliers"]
    if trend_state == "PAUSE":
        return mult_cfg["pause"]
    if trend_state == "NEUTRAL":
        return mult_cfg["neutral"]
    if trend_state == "ACCUMULATE":
        if valuation == ValuationTag.UNDERVALUED:
            return mult_cfg["undervalued_accumulate"]
        if valuation == ValuationTag.OVERVALUED:
            return mult_cfg["overvalued_accumulate"]
        return mult_cfg["fair_accumulate"]
    return 0.0


def allocate_sip(
    picks: List[FundamentalPick],
    trends: Dict[str, TrendSignal],
    cfg: dict,
    regime_cautious: bool,
) -> List[SIPAction]:
    base = cfg["sip"]["base_amount"]
    min_stocks = cfg["constraints"]["min_stocks"]
    max_stocks = cfg["constraints"]["max_stocks"]

    selected = picks[:max_stocks]
    if len(selected) < min_stocks:
        selected = picks[:min(len(picks), min_stocks)]

    actions: List[SIPAction] = []
    for p in selected:
        trend = trends.get(p.fundamentals.ticker)
        if not trend:
            continue
        m = _multiplier(p.valuation.tag, trend.state, cfg)
        alloc = base * m
        notes = []
        if regime_cautious:
            alloc *= (1 - cfg["regime"]["reduce_fraction_if_below_200dma"])
            notes.append("Regime dampener applied")
        if m == 0:
            notes.append("SIP paused by trend")
        actions.append(
            SIPAction(
                ticker=p.fundamentals.ticker,
                name=p.fundamentals.name,
                sector=p.fundamentals.sector,
                fundamental_score=p.score.score,
                valuation=p.valuation.tag.value,
                trend_state=trend.state,
                allocation_multiplier=round(m, 2),
                recommended_sip=round(alloc, 2),
                notes="; ".join(notes),
            )
        )
    return actions
