import argparse
import datetime as dt
from pathlib import Path
from typing import Iterable, List, Tuple

import pandas as pd
import yfinance as yf

# Broad NSE universe (large + liquid midcaps), cleaned to avoid failing tickers
UNIVERSE: List[str] = [
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


def chunked(seq: List[str], size: int) -> Iterable[List[str]]:
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def fetch_history(tickers: List[str], start: dt.date, end: dt.date) -> pd.DataFrame:
    frames: List[pd.DataFrame] = []
    for batch in chunked(tickers, 40):
        data = yf.download(
            batch,
            start=start,
            end=end,
            interval="1d",
            auto_adjust=True,
            progress=False,
            group_by="ticker",
        )
        if data.empty:
            continue
        if isinstance(data.columns, pd.MultiIndex):
            prices = data.xs("Close", axis=1, level=1, drop_level=True)
        else:
            prices = data[["Close"]]
            prices.columns = batch[:1]
        frames.append(prices)
    if not frames:
        raise RuntimeError("No price data fetched")
    combined = pd.concat(frames, axis=1).sort_index()
    combined = combined.loc[:, ~combined.columns.duplicated()]
    combined = combined.dropna(axis=1, thresh=int(0.8 * len(combined)))
    return combined


def compute_scores(window: pd.DataFrame) -> pd.DataFrame:
    ret1m = window.pct_change(21).iloc[-1] * 100
    ret3m = window.pct_change(63).iloc[-1] * 100
    ret6m = window.pct_change(126).iloc[-1] * 100
    vol = window.pct_change().rolling(63).std().iloc[-1] * (252**0.5) * 100
    score = 0.3 * ret1m + 0.4 * ret3m + 0.3 * ret6m
    out = pd.DataFrame({"1m%": ret1m, "3m%": ret3m, "6m%": ret6m, "vol%": vol, "score": score})
    out = out.dropna()
    return out


def run_backtest(
    prices: pd.DataFrame,
    top_n: int = 8,
    vol_cap: float = 40.0,
    lookback_days: int = 200,
    freq: str = "W-FRI",
) -> Tuple[pd.DataFrame, pd.Series]:
    dates = prices.resample(freq).last().index
    equity = 1.0
    equity_curve: List[Tuple[pd.Timestamp, float]] = []
    daily_returns: List[float] = []

    for i in range(1, len(dates) - 1):
        end = dates[i]
        window = prices.loc[:end].tail(lookback_days)
        if len(window) < lookback_days:
            continue
        scores = compute_scores(window)
        filtered = scores[(scores["vol%"] < vol_cap) & (scores["3m%"] > 0) & (scores["6m%"] > 0)]
        picks = filtered.sort_values("score", ascending=False).head(top_n)
        if picks.empty:
            continue
        period = prices.loc[end : dates[i + 1], picks.index]
        period_ret = period.pct_change().iloc[1:]
        if period_ret.empty:
            continue
        weight = 1.0 / len(picks)
        port_ret = period_ret.mul(weight).sum(axis=1)
        for ts, r in port_ret.items():
            equity *= 1 + r
            equity_curve.append((ts, equity))
            daily_returns.append(r)

    if not equity_curve:
        raise RuntimeError("No equity data produced in backtest")

    curve_df = pd.DataFrame(equity_curve, columns=["date", "equity"]).set_index("date")
    daily = pd.Series(daily_returns, index=curve_df.index)
    return curve_df, daily


def performance_stats(curve: pd.DataFrame, daily: pd.Series) -> dict:
    total_days = len(daily)
    cagr = curve["equity"].iloc[-1] ** (252 / total_days) - 1 if total_days else 0.0
    vol = daily.std() * (252**0.5) if total_days else 0.0
    sharpe = (daily.mean() * 252) / vol if vol else 0.0
    roll_max = curve["equity"].cummax()
    drawdown = curve["equity"] / roll_max - 1
    max_dd = drawdown.min() if not drawdown.empty else 0.0
    return {
        "CAGR": cagr,
        "Vol": vol,
        "Sharpe": sharpe,
        "MaxDD": max_dd,
        "FinalEquity": curve["equity"].iloc[-1],
        "LengthDays": total_days,
    }


def save_backtest(curve: pd.DataFrame, stats: dict, picks: pd.DataFrame, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_file = out_dir / f"backtest-{ts}.txt"
    lines: List[str] = []
    lines.append("Backtest summary")
    lines.append(f"CAGR: {stats['CAGR']*100:0.2f}% | Vol: {stats['Vol']*100:0.2f}% | Sharpe: {stats['Sharpe']:0.2f} | MaxDD: {stats['MaxDD']*100:0.2f}%")
    lines.append(f"Final equity: {stats['FinalEquity']:0.2f} | Days: {stats['LengthDays']}")
    lines.append("")
    lines.append("Most recent signal ranks (top 15):")
    head = picks.sort_values("score", ascending=False).head(15)
    for idx, row in head.iterrows():
        lines.append(
            f"- {idx}: score {row['score']:0.1f} | 1m {row['1m%']:0.1f}% | 3m {row['3m%']:0.1f}% | 6m {row['6m%']:0.1f}% | vol {row['vol%']:0.1f}%"
        )
    out_file.write_text("\n".join(lines))
    return out_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Momentum-vol backtest for NSE universe")
    parser.add_argument("--start", type=str, default="2019-01-01", help="Start date YYYY-MM-DD")
    parser.add_argument("--end", type=str, default=dt.date.today().isoformat(), help="End date YYYY-MM-DD")
    parser.add_argument("--top", type=int, default=8, help="Number of picks each rebalance")
    parser.add_argument("--volcap", type=float, default=40.0, help="Volatility cap (pct)")
    parser.add_argument("--freq", type=str, default="W-FRI", help="Rebalance frequency (Pandas offset, e.g., ME for month-end, W-FRI for weekly)")
    args = parser.parse_args()

    start = dt.datetime.fromisoformat(args.start).date()
    end = dt.datetime.fromisoformat(args.end).date()

    prices = fetch_history(UNIVERSE, start, end)
    scores = compute_scores(prices.tail(200))
    curve, daily = run_backtest(prices, top_n=args.top, vol_cap=args.volcap, freq=args.freq)
    stats = performance_stats(curve, daily)
    saved = save_backtest(curve, stats, scores, Path("reports"))

    print(f"Backtest saved to {saved}")
    print(f"CAGR {stats['CAGR']*100:0.2f}%, MaxDD {stats['MaxDD']*100:0.2f}%, Sharpe {stats['Sharpe']:0.2f}")


if __name__ == "__main__":
    main()
