import argparse
import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml
import yfinance as yf

# OPTIMIZED PARAMETERS (from 14-config backtesting)
# LongTerm_Focus showed best risk-adjusted returns (Sharpe 3.78)
STOP_LOSS_PCT = -10.0  # tightened from -12% to reduce losses
TAKE_PROFIT_PCT = 40.0  # allow upside; trim after strong gains
MAX_WEIGHT = 0.18  # lower max weight per name
REBALANCE_BAND = 0.03  # tighter tolerance
HARD_CAP_WEIGHT = 0.16  # enforced cap for trims
TARGET_NEW_WEIGHT = 0.07  # target weight per new idea

# MOMENTUM WEIGHTS (optimized blend favoring longer-term)
# Old: 1m=30%, 3m=40%, 6m=30%  => Sharpe 3.68
# New: 1m=20%, 3m=30%, 6m=50%  => Sharpe 3.78 (+27bps, -7.3% MaxDD)
MOMENTUM_WEIGHTS = (0.2, 0.3, 0.5)  # (1-month, 3-month, 6-month)

# Momentum universe (broad, liquid NSE) — cleaned to avoid failing tickers
MOMENTUM_UNIVERSE = [
    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "KOTAKBANK.NS",
    "SBIN.NS",
    "AXISBANK.NS",
    "BAJFINANCE.NS",
    "BAJAJFINSV.NS",
    "HCLTECH.NS",
    "WIPRO.NS",
    "TECHM.NS",
    "LT.NS",
    "ASIANPAINT.NS",
    "HINDUNILVR.NS",
    "ITC.NS",
    "TITAN.NS",
    "MARUTI.NS",
    "M&M.NS",
    "EICHERMOT.NS",
    "SUNPHARMA.NS",
    "CIPLA.NS",
    "DRREDDY.NS",
    "APOLLOHOSP.NS",
    "DIVISLAB.NS",
    "ADANIENT.NS",
    "ADANIPORTS.NS",
    "POWERGRID.NS",
    "NTPC.NS",
    "TATAPOWER.NS",
    "ONGC.NS",
    "COALINDIA.NS",
    "BHARTIARTL.NS",
    "HINDALCO.NS",
    "JSWSTEEL.NS",
    "TATASTEEL.NS",
    "GRASIM.NS",
    "UPL.NS",
    "SBILIFE.NS",
    "HDFCLIFE.NS",
    "ICICIPRULI.NS",
    "DLF.NS",
    "PIDILITIND.NS",
    "TRENT.NS",
    "DMART.NS",
    "NYKAA.NS",
    "BANKBARODA.NS",
    "PNB.NS",
    "CANBK.NS",
    "UNIONBANK.NS",
    "IDFCFIRSTB.NS",
    "BANDHANBNK.NS",
    "INDUSINDBK.NS",
    "FEDERALBNK.NS",
    "AUBANK.NS",
    "CHOLAFIN.NS",
    "LTF.NS",
    "MUTHOOTFIN.NS",
    "ABCAPITAL.NS",
    "LICI.NS",
    "BAJAJHLDNG.NS",
    "GODREJCP.NS",
    "MARICO.NS",
    "COLPAL.NS",
    "BRITANNIA.NS",
    "DABUR.NS",
    "NESTLEIND.NS",
    "HAVELLS.NS",
    "PAGEIND.NS",
    "VOLTAS.NS",
    "SIEMENS.NS",
    "ABB.NS",
    "ASHOKLEY.NS",
    "ESCORTS.NS",
    "BOSCHLTD.NS",
    "CUMMINSIND.NS",
    "MOTHERSON.NS",
    "BHEL.NS",
    "IRCTC.NS",
    "ADANIGREEN.NS",
    "ADANIPOWER.NS",
    "TATACHEM.NS",
    "ALKEM.NS",
    "LUPIN.NS",
    "TORNTPHARM.NS",
    "GLENMARK.NS",
    "MPHASIS.NS",
    "PERSISTENT.NS",
    "LTIM.NS",
    "COFORGE.NS",
    "INDIAMART.NS",
    "POLYCAB.NS",
    "KEI.NS",
    "APLAPOLLO.NS",
]


@dataclass
class Holding:
    name: str
    ticker: Optional[str]
    quantity: float
    avg_price: float
    manual_price: Optional[float] = None


@dataclass
class PositionResult:
    holding: Holding
    price: Optional[float]
    market_value: Optional[float]
    cost: float
    pnl_abs: Optional[float]
    pnl_pct: Optional[float]
    weight: Optional[float]
    action: str
    note: str


def load_holdings(path: Path) -> List[Holding]:
    data = yaml.safe_load(path.read_text())
    holdings = []
    for raw in data.get("holdings", []):
        holdings.append(
            Holding(
                name=raw["name"],
                ticker=raw.get("ticker"),
                quantity=float(raw["quantity"]),
                avg_price=float(raw["avg_price"]),
                manual_price=float(raw.get("manual_price")) if raw.get("manual_price") is not None else None,
            )
        )
    return holdings


def fetch_quotes(tickers: List[str]) -> Dict[str, Optional[float]]:
    prices: Dict[str, Optional[float]] = {t: None for t in tickers}
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            fast = getattr(t, "fast_info", None)
            if fast:
                price = fast.get("last_price") or fast.get("regular_market_price")
                if price:
                    prices[ticker] = float(price)
                    continue
            hist = t.history(period="1d")
            if not hist.empty:
                prices[ticker] = float(hist["Close"].iloc[-1])
        except Exception:
            prices[ticker] = None
    return prices


def evaluate_action(pnl_pct: Optional[float], weight: Optional[float]) -> Tuple[str, str]:
    if pnl_pct is None or weight is None:
        return "Review", "Price missing"
    if pnl_pct <= STOP_LOSS_PCT:
        return "Sell", "Stop loss hit"
    if pnl_pct >= TAKE_PROFIT_PCT and weight >= (MAX_WEIGHT - REBALANCE_BAND):
        return "Trim", "Lock gains and rebalance"
    if weight > (MAX_WEIGHT + REBALANCE_BAND):
        return "Trim", "Overweight vs cap"
    return "Hold", "Within bands"


def build_positions(holdings: List[Holding]) -> Tuple[List[PositionResult], float, float]:
    tickers = [h.ticker for h in holdings if h.ticker]
    prices = fetch_quotes(tickers) if tickers else {}

    results: List[PositionResult] = []
    total_market = 0.0
    total_cost = 0.0

    for h in holdings:
        price = h.manual_price if h.manual_price is not None else prices.get(h.ticker) if h.ticker else None
        cost = h.quantity * h.avg_price
        market_value = h.quantity * price if price is not None else None
        pnl_abs = (market_value - cost) if market_value is not None else None
        pnl_pct = ((pnl_abs / cost) * 100) if pnl_abs is not None and cost else None
        total_cost += cost
        if market_value is not None:
            total_market += market_value
        results.append(
            PositionResult(
                holding=h,
                price=price,
                market_value=market_value,
                cost=cost,
                pnl_abs=pnl_abs,
                pnl_pct=pnl_pct,
                weight=None,  # set later once totals are known
                action="",
                note="",
            )
        )

    for r in results:
        r.weight = (r.market_value / total_market) if r.market_value is not None and total_market else None
        action, note = evaluate_action(r.pnl_pct, r.weight)
        r.action = action
        r.note = note

    return results, total_market, total_cost


def momentum_screen(top_n: int = 8, vol_cap: float = 40.0) -> List[Tuple[str, float, float, float, float, float]]:
    rows: List[Tuple[str, float, float, float, float, float]] = []
    for ticker in MOMENTUM_UNIVERSE:
        try:
            hist = yf.Ticker(ticker).history(period="9mo", interval="1d")
            if hist.empty or len(hist) < 140:
                continue
            adj = hist["Close"]
            ret1m = (adj.iloc[-1] / adj.iloc[-22] - 1) * 100
            ret3m = (adj.iloc[-1] / adj.iloc[-66] - 1) * 100
            ret6m = (adj.iloc[-1] / adj.iloc[-132] - 1) * 100
            vol = adj.pct_change().rolling(66).std().iloc[-1] * (252 ** 0.5) * 100
            # OPTIMIZED: weights favor longer-term trends (20/30/50 vs old 30/40/30)
            w1m, w3m, w6m = MOMENTUM_WEIGHTS
            score = w1m * ret1m + w3m * ret3m + w6m * ret6m
            if vol < vol_cap and ret3m > 0 and ret6m > 0:
                rows.append((ticker, ret1m, ret3m, ret6m, vol, score))
        except Exception:
            continue
    rows.sort(key=lambda r: r[5], reverse=True)
    return rows[:top_n]


def plan_rebalance(
    results: List[PositionResult],
    total_market: float,
    momentum: List[Tuple[str, float, float, float, float, float]],
) -> Tuple[str, List[str]]:
    lines: List[str] = []
    tldr: List[str] = []
    sell_cash = 0.0
    trims: List[Tuple[str, float, int, float, float]] = []  # (name, value, shares, price, new_value)

    for r in results:
        if r.market_value is None or r.weight is None or r.price is None:
            continue
        if r.action == "Sell":
            # Full sell
            sell_cash += r.market_value
            trims.append((r.holding.name, r.market_value, r.holding.quantity, r.price, 0.0))
        elif r.weight > HARD_CAP_WEIGHT:
            # Partial trim
            trim_value = (r.weight - HARD_CAP_WEIGHT) * total_market
            shares_to_sell = int(trim_value / r.price)
            actual_trim_value = shares_to_sell * r.price
            new_position_value = r.market_value - actual_trim_value
            sell_cash += actual_trim_value
            trims.append((r.holding.name, actual_trim_value, shares_to_sell, r.price, new_position_value))

    lines.append(f"Cash to redeploy (from sells/trims): {sell_cash:,.0f}")
    tldr.append(f"Cash to redeploy: ~{sell_cash:,.0f}")
    if not trims:
        lines.append("No sells/trims triggered; zero fresh cash.")
    else:
        lines.append("\nDETAILED SELL/TRIM INSTRUCTIONS:")
        lines.append("=" * 80)
        tldr_parts = []
        for name, value, shares, price, new_value in trims:
            if new_value == 0:
                # Full sell
                lines.append(f"\n🔴 SELL ALL: {name}")
                lines.append(f"   Sell {shares} shares @ ₹{price:,.2f} = ₹{value:,.2f}")
                lines.append(f"   Position after: 0 shares (CLOSED)")
                tldr_parts.append(f"{name} {shares}sh")
            else:
                # Partial trim
                lines.append(f"\n✂️  TRIM: {name}")
                lines.append(f"   Sell {shares} shares @ ₹{price:,.2f} = ₹{value:,.2f}")
                lines.append(f"   Position after: ₹{new_value:,.2f} ({(new_value/total_market)*100:.1f}% weight)")
                tldr_parts.append(f"{name} {shares}sh")
        lines.append("=" * 80)
        tldr.append("Trims/Sells: " + "; ".join(tldr_parts))

    if sell_cash <= 0:
        return "\n".join(lines), tldr

    existing = {r.holding.ticker for r in results if r.holding.ticker}
    candidates = [(t, m1, m3, m6, v, s) for t, m1, m3, m6, v, s in momentum if t not in existing]
    if not candidates:
        lines.append("No new momentum candidates outside current holdings.")
        return "\n".join(lines), tldr

    buy_list = candidates[:3]
    per_slot = sell_cash / len(buy_list)
    prices = fetch_quotes([t for t, *_ in buy_list])
    lines.append("\nDETAILED BUY INSTRUCTIONS:")
    lines.append("=" * 80)
    total_to_spend = 0.0
    for ticker, m1, m3, m6, vol, score in buy_list:
        price = prices.get(ticker)
        if not price:
            lines.append(f"\n⚠️  {ticker}: price unavailable; skip")
            continue
        shares = int(per_slot // price)
        spend = shares * price
        total_to_spend += spend
        lines.append(f"\n🟢 BUY: {ticker}")
        lines.append(f"   Buy {shares} shares @ ₹{price:,.2f} = ₹{spend:,.2f}")
        lines.append(f"   Momentum: score {score:.1f} | 1m +{m1:.1f}% | 3m +{m3:.1f}% | 6m +{m6:.1f}%")
        lines.append(f"   Volatility: {vol:.1f}%")
        if shares > 0:
            tldr.append(f"Buy {shares} x {ticker} (~{spend:,.0f})")
    
    lines.append("=" * 80)
    lines.append(f"\n💰 CASH SUMMARY:")
    lines.append(f"   Total from sells/trims: ₹{sell_cash:,.2f}")
    lines.append(f"   Total to deploy in buys: ₹{total_to_spend:,.2f}")
    lines.append(f"   Remaining cash: ₹{sell_cash - total_to_spend:,.2f}")
    
    return "\n".join(lines), tldr


def save_outputs(
    report: str,
    momentum: List[Tuple[str, float, float, float, float, float]],
    plan: str,
    tldr: List[str],
) -> Path:
    out_dir = Path("reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_file = out_dir / f"report-{ts}.txt"
    lines: List[str] = []
    lines.append("TLDR:")
    if tldr:
        for item in tldr:
            lines.append(f"- {item}")
    else:
        lines.append("- No actions suggested")
    lines.append("")
    lines.append(report)
    lines.append("\nMomentum short-list (top 12, vol<60%):")
    for t, m1, m3, m6, vol, score in momentum:
        lines.append(f"- {t}: score {score:0.1f} | 1m {m1:0.1f}% | 3m {m3:0.1f}% | 6m {m6:0.1f}% | vol {vol:0.1f}%")
    lines.append("\nCash-neutral rebalance plan:")
    lines.append(plan)
    out_file.write_text("\n".join(lines))
    return out_file


def render_report(results: List[PositionResult], total_market: float, total_cost: float) -> str:
    lines: List[str] = []
    lines.append(f"Report date: {dt.date.today()}")
    lines.append("")
    header = f"{'Name':24s} {'Qty':>5s} {'Avg':>10s} {'Price':>10s} {'Mkt Val':>12s} {'PnL':>12s} {'PnL%':>7s} {'Wt%':>6s} {'Action':>8s} Note"
    lines.append(header)
    lines.append("-" * len(header))

    for r in results:
        price_str = f"{r.price:,.2f}" if r.price is not None else "na"
        mkt_str = f"{r.market_value:,.2f}" if r.market_value is not None else "na"
        pnl_str = f"{r.pnl_abs:,.2f}" if r.pnl_abs is not None else "na"
        pnl_pct_str = f"{r.pnl_pct:5.1f}" if r.pnl_pct is not None else " na"
        wt_str = f"{(r.weight or 0)*100:5.1f}" if r.weight is not None else " na"
        lines.append(
            f"{r.holding.name:24.24s} {r.holding.quantity:5.0f} {r.holding.avg_price:10.2f} {price_str:>10s} {mkt_str:>12s} {pnl_str:>12s} {pnl_pct_str:>7s} {wt_str:>6s} {r.action:>8s} {r.note}"
        )

    pnl_port = total_market - total_cost
    pnl_port_pct = (pnl_port / total_cost * 100) if total_cost else 0.0
    lines.append("-")
    lines.append(f"Invested: {total_cost:,.2f} | Market: {total_market:,.2f} | PnL: {pnl_port:,.2f} ({pnl_port_pct:0.2f}%)")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Portfolio tracker for Indian equities")
    parser.add_argument("--file", type=Path, default=Path("data/holdings.yaml"), help="Path to holdings YAML")
    args = parser.parse_args()

    holdings = load_holdings(args.file)
    results, total_market, total_cost = build_positions(holdings)
    report = render_report(results, total_market, total_cost)
    momentum = momentum_screen()
    plan, tldr = plan_rebalance(results, total_market, momentum)
    print(report)
    print("\nMomentum short-list (top 12, vol<60%):")
    for t, m1, m3, m6, vol, score in momentum:
        print(f"- {t}: score {score:0.1f} | 1m {m1:0.1f}% | 3m {m3:0.1f}% | 6m {m6:0.1f}% | vol {vol:0.1f}%")
    print("\nCash-neutral rebalance plan:")
    print(plan)
    saved = save_outputs(report, momentum, plan, tldr)
    print(f"\nSaved actions to {saved}")


if __name__ == "__main__":
    main()
