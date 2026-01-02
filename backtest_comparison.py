#!/usr/bin/env python3
"""
BACKTEST COMPARISON: Multi-Factor vs Top6_SL8_Hybrid
Simplified approach focusing on signal quality validation
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

try:
    from nifty500_universe import NIFTY500_TICKERS
    PROBLEMATIC = {
        'CEAT.NS', 'PVR.NS', 'EQUITAS.NS', 'MINDTREE.NS', 'DRREDDYS.NS',
        'INOXLEISUR.NS', 'JSW.NS', 'ALEMBICPH.NS', 'AARTI.NS', 'ZOMATO.NS',
        'UJJIVAN.NS', 'DCB.NS', 'CARTRADETECH.NS', 'CADILAHC.NS', 'L&TFH.NS',
        'VARUN.NS', 'ABBOTINDIA.NS', 'PHOENIXLTD.NS', 'TATAMOTORS.NS', 'NAVABREXIM.NS',
        'NARAYANA.NS', 'PRISMCEM.NS', 'WELSPUNIND.NS', 'RAMSINFO.NS', 'ZENSAR.NS',
        'INFOSYS.NS', 'IIFLWAM.NS', 'TATACHEMICALS.NS', 'TATACOFFEE.NS', 'BATA.NS',
        'ADITYADK.NS', 'COX&KINGS.NS', 'HBLPOWER.NS', 'TECHNICALA.NS', 'AMARAJABAT.NS',
        'BHARAT FORGE.NS', 'SONA.NS', 'SAMVARDHNA.NS', 'HINDWARE.NS', 'SWANENERGY.NS',
        'ADANITRANS.NS', 'ORIENTGREEN.NS', 'WEBSOL.NS', 'BOROSIL.NS', 'ORIENTALCARB.NS',
        'GATI.NS', 'AEGISCHEM.NS', 'VRL.NS', 'SIYARAM.NS', 'KPR.NS',
        'FINOLEX.NS', 'RELAXOHOME.NS', 'KALPATPOWR.NS', 'CENTURYTEXT.NS', 'APTECH.NS',
        'NIITTECH.NS', 'FIRSTSOURCE.NS', 'HEXAWARE.NS', 'BALRAMPUR.NS', 'DHAMPUR.NS',
        'FINOLEXIND.NS', 'INDIHOTEL.NS', 'PEL.NS', 'ENGINEERSIN.NS', 'TV18BRDCST.NS', 'INFOE.NS'
    }
    TICKERS = [t for t in NIFTY500_TICKERS if t not in PROBLEMATIC]
except:
    TICKERS = []

def chunked(iterable, n):
    for i in range(0, len(iterable), n):
        yield iterable[i:i+n]

def fetch_history(tickers, start_date, end_date):
    frames = []
    for batch in chunked(tickers, 50):
        try:
            data = yf.download(batch, start=start_date, end=end_date, interval="1d", 
                             auto_adjust=True, progress=False, group_by="ticker")
            if data.empty:
                continue
            if isinstance(data.columns, pd.MultiIndex):
                prices = data.xs("Close", axis=1, level=1, drop_level=True)
            else:
                prices = data[["Close"]]
                prices.columns = batch[:1]
            frames.append(prices)
        except:
            continue
    
    if not frames:
        return pd.DataFrame()
    
    combined = pd.concat(frames, axis=1).sort_index()
    combined = combined.loc[:, ~combined.columns.duplicated()]
    combined = combined.dropna(axis=1, thresh=int(0.8 * len(combined)))
    return combined

def calculate_momentum(col):
    """Calculate momentum score"""
    if len(col) < 126:
        return 0
    ret1m = col.pct_change(21, fill_method=None).iloc[-1] * 100 if len(col) >= 21 else 0
    ret3m = col.pct_change(63, fill_method=None).iloc[-1] * 100 if len(col) >= 63 else 0
    ret6m = col.pct_change(126, fill_method=None).iloc[-1] * 100 if len(col) >= 126 else 0
    ret1m = ret1m if not pd.isna(ret1m) else 0
    ret3m = ret3m if not pd.isna(ret3m) else 0
    ret6m = ret6m if not pd.isna(ret6m) else 0
    return 0.3 * ret1m + 0.4 * ret3m + 0.3 * ret6m

def calculate_quality(col):
    """Calculate trend quality score"""
    if len(col) < 50:
        return 0
    prices_6m = col.iloc[-126:]
    sma20 = prices_6m.rolling(20).mean()
    sma50 = prices_6m.rolling(50).mean()
    trend_strength = np.abs(sma20 - sma50) / sma50 * 100
    daily_returns = prices_6m.pct_change().dropna()
    volatility = daily_returns.std()
    stability = 1.0 / (1.0 + volatility * 10)
    quality = trend_strength.iloc[-1] * stability if not pd.isna(trend_strength.iloc[-1]) else 0
    return quality

def calculate_sharpe(col):
    """Calculate Sharpe ratio"""
    if len(col) < 2:
        return 0
    returns = col.pct_change().dropna()
    mean_ret = returns.mean()
    std_ret = returns.std()
    sharpe = (mean_ret / (std_ret + 1e-10)) * np.sqrt(252)
    return sharpe if not pd.isna(sharpe) else 0

def calculate_volatility(col):
    """Calculate volatility penalty"""
    if len(col) < 2:
        return 0
    returns = col.pct_change().dropna()
    annual_vol = returns.std() * np.sqrt(252)
    risk_penalty = -annual_vol / (1.0 + annual_vol) * 100
    return risk_penalty

def get_composite_score(prices, date, ticker):
    """Calculate composite score for a ticker at a date"""
    window = prices.loc[:date, ticker]
    
    momentum = calculate_momentum(window)
    quality = calculate_quality(window)
    sharpe = calculate_sharpe(window)
    volatility = calculate_volatility(window)
    
    # Normalize to 0-100
    momentum_norm = max(0, min(100, momentum + 50))  # Shift to 0-100
    quality_norm = max(0, min(100, quality * 20))  # Scale quality
    sharpe_norm = max(0, min(100, sharpe * 10 + 50))  # Shift sharpe
    volatility_norm = volatility  # Already -0 to -50
    
    # Composite with same weights
    composite = (0.35 * momentum_norm + 
                 0.25 * quality_norm + 
                 (-0.15) * volatility_norm + 
                 0.15 * sharpe_norm)
    
    return composite, momentum, quality

def run_backtest_comparison(prices, start_date, end_date):
    """Run simplified backtest comparing pure momentum vs multi-factor"""
    
    portfolio_momentum = {}
    portfolio_multifactor = {}
    cash_momentum = 100000.0
    cash_multifactor = 100000.0
    equity_momentum = []
    equity_multifactor = []
    
    trading_dates = prices.resample('W-FRI').last().dropna(how='all').index
    actual_dates = [d for d in trading_dates if d in prices.index]
    
    for date in actual_dates[:]:  # Process all dates
        current_prices = prices.loc[date].dropna()
        
        if len(current_prices) < 10:
            continue
        
        # Calculate scores for all stocks
        scores_momentum = {}
        scores_multifactor = {}
        
        for ticker in prices.columns:
            if ticker not in current_prices.index or pd.isna(current_prices[ticker]):
                continue
            
            window = prices.loc[:date, ticker].dropna()
            if len(window) < 126:
                continue
            
            # Momentum only
            mom = calculate_momentum(window)
            scores_momentum[ticker] = mom
            
            # Multi-factor
            comp, _, _ = get_composite_score(prices, date, ticker)
            scores_multifactor[ticker] = comp
        
        if not scores_momentum or not scores_multifactor:
            continue
        
        # Get top 6 for each approach
        top_momentum = sorted(scores_momentum.items(), key=lambda x: x[1], reverse=True)[:6]
        top_multifactor = sorted(scores_multifactor.items(), key=lambda x: x[1], reverse=True)[:6]
        
        # Process stop-losses and rebalance for momentum
        portfolio_value_m = cash_momentum
        for ticker in list(portfolio_momentum.keys()):
            if ticker in current_prices.index:
                shares = portfolio_momentum[ticker]['shares']
                entry = portfolio_momentum[ticker]['entry']
                current = current_prices[ticker]
                pnl = (current - entry) / entry * 100
                if pnl <= -8.0:
                    cash_momentum += shares * current
                    del portfolio_momentum[ticker]
                else:
                    portfolio_value_m += shares * current
        
        # Same for multi-factor
        portfolio_value_mf = cash_multifactor
        for ticker in list(portfolio_multifactor.keys()):
            if ticker in current_prices.index:
                shares = portfolio_multifactor[ticker]['shares']
                entry = portfolio_multifactor[ticker]['entry']
                current = current_prices[ticker]
                pnl = (current - entry) / entry * 100
                if pnl <= -8.0:
                    cash_multifactor += shares * current
                    del portfolio_multifactor[ticker]
                else:
                    portfolio_value_mf += shares * current
        
        # Rebalance momentum (equal weight 6 stocks)
        target_per = portfolio_value_m / 6.0
        for ticker, _ in top_momentum:
            if ticker not in current_prices.index:
                continue
            if ticker in portfolio_momentum:
                portfolio_momentum[ticker]['shares'] = int(target_per / current_prices[ticker])
            else:
                shares = int(target_per / current_prices[ticker])
                if shares > 0 and shares * current_prices[ticker] <= cash_momentum:
                    portfolio_momentum[ticker] = {'shares': shares, 'entry': current_prices[ticker]}
                    cash_momentum -= shares * current_prices[ticker]
        
        # Rebalance multi-factor (equal weight 6 stocks)
        target_per = portfolio_value_mf / 6.0
        for ticker, _ in top_multifactor:
            if ticker not in current_prices.index:
                continue
            if ticker in portfolio_multifactor:
                portfolio_multifactor[ticker]['shares'] = int(target_per / current_prices[ticker])
            else:
                shares = int(target_per / current_prices[ticker])
                if shares > 0 and shares * current_prices[ticker] <= cash_multifactor:
                    portfolio_multifactor[ticker] = {'shares': shares, 'entry': current_prices[ticker]}
                    cash_multifactor -= shares * current_prices[ticker]
        
        # Record portfolio values
        pv_m = cash_momentum + sum(p['shares'] * current_prices.get(t, 0) for t, p in portfolio_momentum.items() if t in current_prices.index)
        pv_mf = cash_multifactor + sum(p['shares'] * current_prices.get(t, 0) for t, p in portfolio_multifactor.items() if t in current_prices.index)
        
        equity_momentum.append({'date': date, 'value': pv_m})
        equity_multifactor.append({'date': date, 'value': pv_mf})
    
    # Calculate metrics for both
    def calc_metrics(equity_curve):
        if len(equity_curve) < 2:
            return {'cagr': 0, 'sharpe': 0, 'maxdd': 0}
        
        df = pd.DataFrame(equity_curve).set_index('date')
        returns = df['value'].pct_change().dropna()
        
        total_return = (df['value'].iloc[-1] / df['value'].iloc[0]) - 1
        years = (df.index[-1] - df.index[0]).days / 365.25
        cagr = ((1 + total_return) ** (1 / years) - 1) * 100 if years > 0 else 0
        
        sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if len(returns) > 1 else 0
        
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        maxdd = drawdown.min() * 100
        
        return {'cagr': cagr, 'sharpe': sharpe, 'maxdd': maxdd}
    
    metrics_m = calc_metrics(equity_momentum)
    metrics_mf = calc_metrics(equity_multifactor)
    
    return metrics_m, metrics_mf

if __name__ == '__main__':
    print("="*100)
    print("BACKTEST COMPARISON: Momentum vs Multi-Factor (2016-2026)")
    print("="*100)
    
    START_DATE = '2016-01-01'
    END_DATE = '2026-01-02'
    
    print(f"\nLoading {len(TICKERS)} stocks...")
    prices = fetch_history(TICKERS, START_DATE, END_DATE)
    
    if prices.empty:
        print("ERROR: No price data!")
        exit(1)
    
    print(f"Loaded {len(prices.columns)} stocks\n")
    print("Running backtest comparison (weekly rebalancing, -8% stop-loss)...\n")
    
    metrics_m, metrics_mf = run_backtest_comparison(prices, START_DATE, END_DATE)
    
    print("="*100)
    print("RESULTS")
    print("="*100)
    print(f"\n{'Strategy':<30} {'CAGR':>12} {'Sharpe':>12} {'MaxDD':>12}")
    print("-"*100)
    print(f"{'Top6_SL8_Hybrid (Baseline)':<30} {35.38:>11.2f}% {4.51:>11.2f} {-13.13:>11.2f}%")
    print(f"{'Momentum Only (Test)':<30} {metrics_m['cagr']:>11.2f}% {metrics_m['sharpe']:>11.2f} {metrics_m['maxdd']:>11.2f}%")
    print(f"{'Multi-Factor (6 Signals)':<30} {metrics_mf['cagr']:>11.2f}% {metrics_mf['sharpe']:>11.2f} {metrics_mf['maxdd']:>11.2f}%")
    print("-"*100)
    
    improvement = metrics_mf['cagr'] - metrics_m['cagr']
    if improvement > 0:
        print(f"\n✅ MULTI-FACTOR BETTER: +{improvement:.2f}% CAGR improvement over pure momentum!")
    else:
        print(f"\n⚠️  MOMENTUM STRONGER: Pure momentum {-improvement:.2f}% better CAGR")
        print(f"    This suggests: Multi-factor adds diversification but reduces returns")
        print(f"    Recommendation: Keep Top6_SL8_Hybrid (pure momentum approach)")
    
    print(f"\nCAGR vs Baseline (35.38%):")
    print(f"  Momentum Test: {metrics_m['cagr'] - 35.38:+.2f}%")
    print(f"  Multi-Factor:  {metrics_mf['cagr'] - 35.38:+.2f}%")
