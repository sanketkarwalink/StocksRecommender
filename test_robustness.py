import datetime as dt
import itertools
import sys
from pathlib import Path

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent))

from strategy_backtest import fetch_history, run_backtest, performance_stats
from nifty500_universe import NIFTY500_TICKERS


def main() -> None:
    print("Parameter Robustness Test")
    print("=" * 60)
    
    # Parameter grid
    top_ns = [6, 8, 10]
    vol_caps = [35.0, 40.0, 45.0]
    freqs = ["W-FRI"]  # Keep weekly for consistency
    
    start = dt.date(2019, 1, 1)
    end = dt.date(2026, 1, 2)
    
    print(f"Fetching {len(NIFTY500_TICKERS)} stocks from {start} to {end}...")
    prices = fetch_history(NIFTY500_TICKERS, start, end)
    print(f"✓ Fetched {len(prices.columns)} valid tickers\n")
    
    results = []
    total = len(top_ns) * len(vol_caps) * len(freqs)
    count = 0
    
    for top_n, vol_cap, freq in itertools.product(top_ns, vol_caps, freqs):
        count += 1
        print(f"[{count}/{total}] Testing: top={top_n}, volcap={vol_cap}, freq={freq}")
        try:
            curve, daily = run_backtest(prices, top_n=top_n, vol_cap=vol_cap, freq=freq)
            stats = performance_stats(curve, daily)
            results.append({
                "top_n": top_n,
                "vol_cap": vol_cap,
                "freq": freq,
                "cagr": stats["CAGR"],
                "maxdd": stats["MaxDD"],
                "sharpe": stats["Sharpe"],
                "final_eq": stats["FinalEquity"],
            })
            print(f"  → CAGR: {stats['CAGR']*100:.2f}%, MaxDD: {stats['MaxDD']*100:.2f}%, Sharpe: {stats['Sharpe']:.2f}\n")
        except Exception as e:
            print(f"  ✗ Failed: {e}\n")
            continue
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY OF PARAMETER ROBUSTNESS")
    print("=" * 60)
    print(f"{'Top':>4} {'VolCap':>7} {'Freq':>7} {'CAGR%':>8} {'MaxDD%':>8} {'Sharpe':>7}")
    print("-" * 60)
    for r in sorted(results, key=lambda x: x["sharpe"], reverse=True):
        print(f"{r['top_n']:>4} {r['vol_cap']:>7.1f} {r['freq']:>7} {r['cagr']*100:>8.2f} {r['maxdd']*100:>8.2f} {r['sharpe']:>7.2f}")
    
    # Save results
    out_dir = Path("reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_file = out_dir / f"robustness-{ts}.txt"
    lines = ["Parameter Robustness Test", "=" * 60, ""]
    lines.append(f"Universe: {len(prices.columns)} NIFTY 500 stocks")
    lines.append(f"Period: {start} to {end}")
    lines.append("")
    lines.append(f"{'Top':>4} {'VolCap':>7} {'Freq':>7} {'CAGR%':>8} {'MaxDD%':>8} {'Sharpe':>7}")
    lines.append("-" * 60)
    for r in sorted(results, key=lambda x: x["sharpe"], reverse=True):
        lines.append(f"{r['top_n']:>4} {r['vol_cap']:>7.1f} {r['freq']:>7} {r['cagr']*100:>8.2f} {r['maxdd']*100:>8.2f} {r['sharpe']:>7.2f}")
    out_file.write_text("\n".join(lines))
    print(f"\n✓ Saved to {out_file}")


if __name__ == "__main__":
    main()
