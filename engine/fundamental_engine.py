from dataclasses import dataclass
from typing import List, Tuple

from data.fundamentals import StockFundamentals, passes_hard_filters, FundamentalScore
from data.valuations import tag_valuation, ValuationResult


@dataclass
class FundamentalPick:
    fundamentals: StockFundamentals
    score: FundamentalScore
    valuation: ValuationResult


def screen_and_score(fundamentals: List[StockFundamentals], cfg: dict) -> List[FundamentalPick]:
    picks: List[FundamentalPick] = []
    for f in fundamentals:
        score = passes_hard_filters(f, cfg)
        if not score.passed_filters:
            continue
        valuation = tag_valuation(f, cfg)
        picks.append(FundamentalPick(fundamentals=f, score=score, valuation=valuation))
    # Sort by score descending
    picks.sort(key=lambda p: p.score.score, reverse=True)
    return picks


def apply_sector_constraints(picks: List[FundamentalPick], cfg: dict) -> List[FundamentalPick]:
    max_positions = cfg["constraints"]["max_sector_positions"]
    override_score = cfg["constraints"]["sector_override_score"]
    filtered: List[FundamentalPick] = []
    sector_counts: dict = {}

    for p in picks:
        sector = p.fundamentals.sector
        count = sector_counts.get(sector, 0)
        if count < max_positions or p.score.score >= override_score:
            filtered.append(p)
            sector_counts[sector] = count + 1
    return filtered
