from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .fundamentals import StockFundamentals


class ValuationTag(str, Enum):
    UNDERVALUED = "UNDERVALUED"
    FAIR = "FAIR"
    OVERVALUED = "OVERVALUED"


@dataclass
class ValuationResult:
    tag: ValuationTag
    notes: str


def tag_valuation(f: StockFundamentals, cfg: dict) -> ValuationResult:
    notes = []
    tag = ValuationTag.FAIR
    vcfg = cfg["valuation"]

    sector_pe = f.sector_pe_median or 0
    if f.pe and sector_pe and f.pe < sector_pe:
        notes.append("PE below sector median")
    elif f.pe and sector_pe and f.pe > sector_pe * 1.2:
        notes.append("PE above sector median")

    if f.peg is not None and f.peg < vcfg["peg_positive_max"]:
        notes.append("PEG < threshold")
    elif f.peg is not None and f.peg > vcfg["peg_positive_max"]:
        notes.append("High PEG")

    is_bfsi = f.sector.upper().startswith(("BANK", "FIN", "NBFC", "INSUR"))
    if not is_bfsi:
        if f.pb < vcfg["pb_ceiling"]:
            notes.append("PB within ceiling")
        else:
            notes.append("PB above ceiling")

    positives = sum(1 for n in notes if "below" in n or "<" in n or "within" in n)
    negatives = len(notes) - positives

    if positives >= 2 and negatives == 0:
        tag = ValuationTag.UNDERVALUED
    elif negatives >= 2 and positives == 0:
        tag = ValuationTag.OVERVALUED
    else:
        tag = ValuationTag.FAIR

    return ValuationResult(tag=tag, notes=", ".join(notes))
