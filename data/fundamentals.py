from dataclasses import dataclass
from typing import List, Optional


@dataclass
class StockFundamentals:
    ticker: str
    name: str
    sector: str
    market_cap_cr: float
    listing_years: float
    adv_cr: float  # average daily traded value in crores
    roce: float
    debt_to_equity: float
    sales_cagr_5y: float
    profit_cagr_5y: float
    fcf_3y_positive: bool
    promoter_holding: float
    promoter_change_pct: float
    pe: float
    pb: float
    peg: Optional[float]
    sector_pe_median: Optional[float]
    revenue_5y: Optional[List[float]] = None
    net_profit_5y: Optional[List[float]] = None
    fcf_3y: Optional[List[float]] = None


@dataclass
class FundamentalScore:
    score: float
    passed_filters: bool
    reasons: List[str]


def passes_hard_filters(f: StockFundamentals, cfg: dict) -> FundamentalScore:
    reasons: List[str] = []
    passed = True

    if f.market_cap_cr < cfg["universe"]["min_market_cap_cr"]:
        passed = False
        reasons.append("Market cap below threshold")
    if f.listing_years < cfg["universe"]["min_listing_years"]:
        passed = False
        reasons.append("Listed years below threshold")
    if f.adv_cr < cfg["universe"]["min_adv_cr"]:
        passed = False
        reasons.append("ADV below threshold")

    fund_cfg = cfg["fundamentals"]
    if f.roce < fund_cfg["min_roce"]:
        passed = False
        reasons.append("ROCE below minimum")
    if f.debt_to_equity > fund_cfg["max_debt_to_equity"]:
        passed = False
        reasons.append("Leverage above maximum")
    if f.sales_cagr_5y < fund_cfg["min_sales_cagr_5y"]:
        passed = False
        reasons.append("Sales CAGR below minimum")
    if f.promoter_holding < fund_cfg["min_promoter_holding"]:
        passed = False
        reasons.append("Promoter holding below minimum")
    if fund_cfg["require_positive_fcf_3y"] and not f.fcf_3y_positive:
        passed = False
        reasons.append("Negative FCF over 3Y")
    if f.profit_cagr_5y < fund_cfg.get("min_profit_cagr_5y", 0):
        passed = False
        reasons.append("Profit CAGR below minimum")

    score = compute_score(f)
    if score < fund_cfg["min_score"]:
        passed = False
        reasons.append("Score below cutoff")

    return FundamentalScore(score=score, passed_filters=passed, reasons=reasons)


def compute_score(f: StockFundamentals) -> float:
    # Weighted score on 0–100 scale
    weights = {
        "roce": 25,
        "sales_cagr": 20,
        "profit_cagr": 15,
        "debt": 15,
        "fcf": 15,
        "promoter": 10,
    }

    score = 0.0
    score += weights["roce"] * min(f.roce / 40, 1)  # cap at 40% ROCE
    score += weights["sales_cagr"] * min(f.sales_cagr_5y / 25, 1)
    score += weights["profit_cagr"] * min(max(f.profit_cagr_5y, 0) / 25, 1)
    debt_factor = max(0.0, (1.0 - (f.debt_to_equity / 1.0)))
    score += weights["debt"] * debt_factor
    score += weights["fcf"] * (1.0 if f.fcf_3y_positive else 0.0)
    promoter_factor = min(max((f.promoter_holding - 45) / 20, 0.0), 1.0)
    score += weights["promoter"] * promoter_factor

    return round(score, 2)
