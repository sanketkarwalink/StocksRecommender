"""
Generate live Top6_SL10 recommendations
Backtest Results: 34.33% CAGR, 4.49 Sharpe, -13.27% MaxDD
"""
import subprocess
import sys

print("🚀 GENERATING LIVE TOP6_SL10 RECOMMENDATIONS")
print("=" * 60)
print("Strategy: Top6_SL10")
print("- Holdings: 6 stocks (equal weight 16.67% each)")
print("- Stop Loss: -10%")
print("- Momentum: 0.3/0.4/0.3 (1m/3m/6m)")
print("- Take Profit: 40%")
print("=" * 60)
print()

# Run portfolio_tool with Top6_SL10 parameters
result = subprocess.run([
    sys.executable, "portfolio_tool.py",
    "--top-n", "6",
    "--stop-loss", "-10.0",
    "--take-profit", "40.0",
    "--max-weight", "0.20"
], capture_output=False)

sys.exit(result.returncode)
