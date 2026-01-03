import csv
from pathlib import Path
from typing import Iterable, List

from data.fundamentals import StockFundamentals


_REQUIRED_COLS = {
    "ticker",
    "name",
    "sector",
    "market_cap_cr",
    "listing_years",
    "adv_cr",
    "roce",
    "debt_to_equity",
    "sales_cagr_5y",
    "profit_cagr_5y",
    "fcf_3y_positive",
    "promoter_holding",
    "promoter_change_pct",
    "pe",
    "pb",
    "peg",
    "sector_pe_median",
}


def _boolify(val: str) -> bool:
    return str(val).strip().lower() in {"true", "1", "yes", "y"}


def load_fundamentals_csv(path: Path, universe: Iterable[str]) -> List[StockFundamentals]:
    rows: List[StockFundamentals] = []
    text = path.read_text(encoding="utf-8")
    reader = csv.DictReader(text.splitlines())
    missing = _REQUIRED_COLS - set(reader.fieldnames or [])
    if missing:
        raise ValueError(f"Fundamentals CSV missing columns: {sorted(missing)}")

    universe_set = set(universe)
    for raw in reader:
        ticker = raw["ticker"].strip()
        if ticker not in universe_set:
            continue
        try:
            rows.append(
                StockFundamentals(
                    ticker=ticker,
                    name=raw["name"].strip(),
                    sector=raw["sector"].strip(),
                    market_cap_cr=float(raw["market_cap_cr"]),
                    listing_years=float(raw["listing_years"]),
                    adv_cr=float(raw["adv_cr"]),
                    roce=float(raw["roce"]),
                    debt_to_equity=float(raw["debt_to_equity"]),
                    sales_cagr_5y=float(raw["sales_cagr_5y"]),
                    profit_cagr_5y=float(raw["profit_cagr_5y"]),
                    fcf_3y_positive=_boolify(raw["fcf_3y_positive"]),
                    promoter_holding=float(raw["promoter_holding"]),
                    promoter_change_pct=float(raw.get("promoter_change_pct", 0.0)),
                    pe=float(raw["pe"]),
                    pb=float(raw["pb"]),
                    peg=float(raw["peg"]) if raw.get("peg") not in (None, "") else None,
                    sector_pe_median=float(raw["sector_pe_median"]) if raw.get("sector_pe_median") not in (None, "") else None,
                )
            )
        except ValueError as exc:
            # Skip bad row but continue processing others
            continue
    return rows
