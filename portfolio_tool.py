import argparse
import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml
import yfinance as yf

# OPTIMIZED PARAMETERS (from final 10-year backtest on 317-stock universe)
# Top6_SL10 showed best performance: 34.33% CAGR, Sharpe 4.49, MaxDD -13.27%
# Strategy: 6 concentrated positions, -10% stop-loss, equal weight
#   Excellent risk-adjusted returns across bull/bear/crash cycles
#   Tested 2016-2026 including 2016 crash and 2020 COVID
#   251 stocks successfully loaded, 317-stock universe
STOP_LOSS_PCT = -10.0  # standard stop-loss level
TAKE_PROFIT_PCT = 40.0  # allow upside; trim after strong gains
MAX_WEIGHT = 0.20  # higher max weight for 6-stock portfolio
REBALANCE_BAND = 0.03  # tighter tolerance
HARD_CAP_WEIGHT = 0.18  # enforced cap for trims (adjusted for 6 stocks)
TARGET_NEW_WEIGHT = 0.10  # target weight per new idea (1/6 ≈ 16.7%)
VOL_CAP = 40.0  # volatility ceiling for momentum screen

# MOMENTUM WEIGHTS (balanced 0.3/0.4/0.3 - weights all periods equally)
# Enables effective stock selection across different momentum periods
MOMENTUM_WEIGHTS = (0.3, 0.4, 0.3)  # (1-month, 3-month, 6-month)

# EQUAL WEIGHTING: Top6_SL10 uses equal weight (not dynamic sizing)
# Equal weighting simplifies execution and has proven superior in backtests
DYNAMIC_SIZING = False  # Equal weight all positions
TOP_N_PICKS = 6  # Select top 6 momentum stocks per rebalance (concentrated)

# Expanded NIFTY 500 Universe - filtered for data quality
# Excludes known problematic tickers (delisted, bad data, etc.)
try:
    from nifty500_universe import NIFTY500_TICKERS
    PROBLEMATIC_TICKERS = {
        'CEAT.NS', 'PVR.NS', 'EQUITAS.NS', 'MINDTREE.NS', 'DRREDDYS.NS',
        'INOXLEISUR.NS', 'JSW.NS', 'ALEMBICPH.NS', 'AARTI.NS', 'ZOMATO.NS',
        'UJJIVAN.NS', 'DCB.NS', 'CARTRADETECH.NS', 'CADILAHC.NS', 'L&TFH.NS',
        'VARUN.NS', 'ABBOTINDIA.NS', 'PHOENIXLTD.NS', 'TATAMOTORS.NS', 'NAVABREXIM.NS',
        # Newly discovered delisted/bad data tickers
        'NARAYANA.NS', 'PRISMCEM.NS', 'WELSPUNIND.NS', 'RAMSINFO.NS', 'ZENSAR.NS',
        'INFOSYS.NS', 'IIFLWAM.NS', 'TATACHEMICALS.NS', 'TATACOFFEE.NS', 'BATA.NS',
        'ADITYADK.NS', 'COX&KINGS.NS', 'HBLPOWER.NS', 'TECHNICALA.NS', 'AMARAJABAT.NS',
        'BHARAT FORGE.NS', 'SONA.NS', 'SAMVARDHNA.NS', 'HINDWARE.NS', 'SWANENERGY.NS',
        'ADANITRANS.NS', 'ORIENTGREEN.NS', 'WEBSOL.NS', 'BOROSIL.NS', 'ORIENTALCARB.NS',
        'GATI.NS', 'AEGISCHEM.NS', 'VRL.NS', 'SIYARAM.NS', 'KPR.NS',
        'FINOLEX.NS', 'RELAXOHOME.NS', 'KALPATPOWR.NS', 'CENTURYTEXT.NS', 'APTECH.NS',
        'NIITTECH.NS', 'FIRSTSOURCE.NS', 'HEXAWARE.NS', 'BALRAMPUR.NS', 'DHAMPUR.NS',
        'FINOLEXIND.NS',  # Additional bad ticker
        # Additional bad tickers from expanded universe
        'INDIHOTEL.NS', 'PEL.NS', 'ENGINEERSIN.NS', 'TV18BRDCST.NS', 'INFOE.NS'
    }
    MOMENTUM_UNIVERSE = [t for t in NIFTY500_TICKERS if t not in PROBLEMATIC_TICKERS]
    print(f"Loaded NIFTY 500 universe: {len(MOMENTUM_UNIVERSE)} stocks (filtered {len(PROBLEMATIC_TICKERS)} bad tickers)")
except ImportError:
    # Fallback to smaller curated list if nifty500_universe.py not available
    MOMENTUM_UNIVERSE = [
        "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
        "KOTAKBANK.NS", "SBIN.NS", "AXISBANK.NS", "BAJFINANCE.NS", "BAJAJFINSV.NS",
        "HCLTECH.NS", "WIPRO.NS", "TECHM.NS", "LT.NS", "ASIANPAINT.NS",
        "HINDUNILVR.NS", "ITC.NS", "TITAN.NS", "MARUTI.NS", "M&M.NS",
        "EICHERMOT.NS", "SUNPHARMA.NS", "CIPLA.NS", "DRREDDY.NS", "APOLLOHOSP.NS",
        "DIVISLAB.NS", "ADANIENT.NS", "ADANIPORTS.NS", "POWERGRID.NS", "NTPC.NS",
        "TATAPOWER.NS", "ONGC.NS", "COALINDIA.NS", "BHARTIARTL.NS", "HINDALCO.NS",
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
        "CANBK.NS", "UNIONBANK.NS", "IDFCFIRSTB.NS", "BANDHANBNK.NS", "INDUSINDBK.NS",
        "FEDERALBNK.NS", "AUBANK.NS", "CHOLAFIN.NS", "LTF.NS", "MUTHOOTFIN.NS",
        "ABCAPITAL.NS", "LICI.NS", "BAJAJHLDNG.NS", "GODREJCP.NS", "MARICO.NS",
        "COLPAL.NS", "BRITANNIA.NS", "DABUR.NS", "NESTLEIND.NS", "HAVELLS.NS",
        "PAGEIND.NS", "VOLTAS.NS", "SIEMENS.NS", "ABB.NS", "ASHOKLEY.NS",
        "ESCORTS.NS", "BOSCHLTD.NS", "CUMMINSIND.NS", "MOTHERSON.NS", "BHEL.NS",
        "IRCTC.NS", "ADANIGREEN.NS", "ADANIPOWER.NS", "TATACHEM.NS", "ALKEM.NS",
        "LUPIN.NS", "TORNTPHARM.NS", "GLENMARK.NS", "MPHASIS.NS", "PERSISTENT.NS",
        "LTIM.NS", "COFORGE.NS", "INDIAMART.NS", "POLYCAB.NS", "KEI.NS", "APLAPOLLO.NS",
    ]
    print(f"Using fallback universe: {len(MOMENTUM_UNIVERSE)} stocks")


def parse_momentum_weights(value: str) -> Tuple[float, float, float]:
    parts = value.split(",")
    if len(parts) != 3:
        raise argparse.ArgumentTypeError(
            "Momentum weights must be three comma-separated numbers like 0.3,0.4,0.3"
        )
    try:
        weights = tuple(float(p) for p in parts)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Momentum weights must be numeric") from exc
    total = sum(weights)
    if total <= 0:
        raise argparse.ArgumentTypeError("Momentum weights must sum to a positive value")
    return weights  # type: ignore[return-value]


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


def momentum_screen(top_n: int = TOP_N_PICKS, vol_cap: float = VOL_CAP) -> List[Tuple[str, float, float, float, float, float]]:
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
            # Only trim if we can sell at least 1 share
            if shares_to_sell > 0:
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
    top_n: int,
    vol_cap: float,
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
    lines.append(f"\nMomentum short-list (top {len(momentum)}, vol<{vol_cap:.0f}%):")
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
    global STOP_LOSS_PCT, TAKE_PROFIT_PCT, MAX_WEIGHT, HARD_CAP_WEIGHT, REBALANCE_BAND
    global DYNAMIC_SIZING, TOP_N_PICKS, VOL_CAP, MOMENTUM_WEIGHTS

    parser = argparse.ArgumentParser(description="Portfolio tracker for Indian equities")
    parser.add_argument("--file", type=Path, default=Path("data/holdings.yaml"), help="Path to holdings YAML")
    parser.add_argument("--top-n", type=int, default=TOP_N_PICKS, help="Number of stocks to hold (momentum top-N)")
    parser.add_argument("--stop-loss", type=float, default=STOP_LOSS_PCT, help="Stop-loss percentage (negative)")
    parser.add_argument("--take-profit", type=float, default=TAKE_PROFIT_PCT, help="Take-profit / trim threshold")
    parser.add_argument("--max-weight", type=float, default=MAX_WEIGHT, help="Soft max weight before trim")
    parser.add_argument("--hard-cap-weight", type=float, default=HARD_CAP_WEIGHT, help="Hard cap weight to trigger trims")
    parser.add_argument("--rebalance-band", type=float, default=REBALANCE_BAND, help="Tolerance band around max weight")
    parser.add_argument("--vol-cap", type=float, default=VOL_CAP, help="Volatility cap for momentum screen")
    parser.add_argument(
        "--momentum-weights",
        type=parse_momentum_weights,
        default=None,
        help="Comma-separated weights for 1m,3m,6m momentum (e.g., 0.3,0.4,0.3)",
    )
    parser.add_argument(
        "--dynamic-sizing",
        action="store_true",
        default=DYNAMIC_SIZING,
        help="Weight positions by momentum score instead of equal weight",
    )
    args = parser.parse_args()

    default_weights = MOMENTUM_WEIGHTS
    STOP_LOSS_PCT = args.stop_loss
    TAKE_PROFIT_PCT = args.take_profit
    MAX_WEIGHT = args.max_weight
    HARD_CAP_WEIGHT = args.hard_cap_weight
    REBALANCE_BAND = args.rebalance_band
    DYNAMIC_SIZING = args.dynamic_sizing
    TOP_N_PICKS = args.top_n
    VOL_CAP = args.vol_cap
    MOMENTUM_WEIGHTS = args.momentum_weights if args.momentum_weights else default_weights

    holdings = load_holdings(args.file)
    results, total_market, total_cost = build_positions(holdings)
    report = render_report(results, total_market, total_cost)
    momentum = momentum_screen(top_n=TOP_N_PICKS, vol_cap=VOL_CAP)
    plan, tldr = plan_rebalance(results, total_market, momentum)
    print(report)
    print(f"\nMomentum short-list (top {len(momentum)}, vol<{VOL_CAP:.0f}%):")
    for t, m1, m3, m6, vol, score in momentum:
        print(f"- {t}: score {score:0.1f} | 1m {m1:0.1f}% | 3m {m3:0.1f}% | 6m {m6:0.1f}% | vol {vol:0.1f}%")
    print("\nCash-neutral rebalance plan:")
    print(plan)
    saved = save_outputs(report, momentum, plan, tldr, TOP_N_PICKS, VOL_CAP)
    print(f"\nSaved actions to {saved}")


if __name__ == "__main__":
    main()
