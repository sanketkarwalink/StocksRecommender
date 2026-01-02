#!/usr/bin/env python3
"""
Test Strategy Improvements - Find the optimal configuration
Tests combinations not yet explored in previous backtests
"""

import pandas as pd
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

def compute_scores(window, momentum_weights):
    w1m, w3m, w6m = momentum_weights
    ret1m = window.pct_change(21, fill_method=None).iloc[-1] * 100
    ret3m = window.pct_change(63, fill_method=None).iloc[-1] * 100
    ret6m = window.pct_change(126, fill_method=None).iloc[-1] * 100
    vol = window.pct_change(fill_method=None).rolling(63).std().iloc[-1] * (252**0.5) * 100
    
    scores = w1m * ret1m + w3m * ret3m + w6m * ret6m
    
    result = pd.DataFrame({
        'score': scores,
        'ret1m': ret1m,
        'ret3m': ret3m,
        'ret6m': ret6m,
        'vol': vol
    })
    return result.dropna()

def run_backtest(prices, start_date, end_date, top_n, vol_cap, stop_loss, 
                momentum_weights, rebal_freq='W-FRI', dynamic_sizing=False):
    portfolio = {}
    cash = 100000.0
    equity_curve = []
    
    for date in prices.resample(rebal_freq).last().dropna(how='all').index:
        current_prices = prices.resample(rebal_freq).last().loc[date]
        valid_prices = current_prices.dropna()
        
        if len(valid_prices) < 10:
            continue
        
        window_start = date - pd.DateOffset(months=6)
        window = prices.loc[window_start:date, valid_prices.index]
        
        if len(window) < 126:
            continue
        
        scores = compute_scores(window, momentum_weights)
        mask = (scores['vol'] < vol_cap) & (scores['ret3m'] > 0) & (scores['ret6m'] > 0)
        filtered = scores[mask].sort_values('score', ascending=False)
        
        if len(filtered) == 0:
            continue
        
        picks = filtered.head(top_n)
        
        portfolio_value = cash
        to_sell = []
        
        for ticker, entry_data in list(portfolio.items()):
            if ticker not in valid_prices.index:
                continue
            current_price = valid_prices[ticker]
            entry_price = entry_data['entry_price']
            shares = entry_data['shares']
            
            position_value = shares * current_price
            portfolio_value += position_value
            
            pct_change = ((current_price - entry_price) / entry_price) * 100
            if pct_change <= stop_loss:
                to_sell.append(ticker)
            elif ticker not in picks.index:
                to_sell.append(ticker)
        
        for ticker in to_sell:
            shares = portfolio[ticker]['shares']
            sell_price = valid_prices[ticker]
            cash += shares * sell_price
            del portfolio[ticker]
        
        portfolio_value = cash
        for ticker in portfolio:
            if ticker in valid_prices.index:
                portfolio_value += portfolio[ticker]['shares'] * valid_prices[ticker]
        
        if dynamic_sizing:
            total_score = picks['score'].sum()
            target_weights = picks['score'] / total_score
        else:
            target_weights = pd.Series(1.0 / len(picks), index=picks.index)
        
        for ticker in picks.index:
            if ticker not in portfolio:
                target_value = portfolio_value * target_weights[ticker]
                current_price = valid_prices[ticker]
                shares_to_buy = int(target_value / current_price)
                
                if shares_to_buy > 0:
                    cost = shares_to_buy * current_price
                    if cost <= cash:
                        portfolio[ticker] = {
                            'shares': shares_to_buy,
                            'entry_price': current_price
                        }
                        cash -= cost
        
        total_value = cash
        for ticker in portfolio:
            if ticker in valid_prices.index:
                total_value += portfolio[ticker]['shares'] * valid_prices[ticker]
        
        equity_curve.append({'date': date, 'value': total_value})
    
    if len(equity_curve) < 2:
        return None
    
    df_equity = pd.DataFrame(equity_curve).set_index('date')
    returns = df_equity['value'].pct_change().dropna()
    
    total_return = (df_equity['value'].iloc[-1] / df_equity['value'].iloc[0]) - 1
    years = (df_equity.index[-1] - df_equity.index[0]).days / 365.25
    cagr = ((1 + total_return) ** (1 / years) - 1) * 100
    
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    max_dd = drawdown.min() * 100
    
    sharpe = (returns.mean() / returns.std()) * (252 ** 0.5) if len(returns) > 1 else 0
    
    return {
        'cagr': cagr,
        'sharpe': sharpe,
        'max_dd': max_dd,
    }

# IMPROVEMENT CONFIGURATIONS TO TEST
CONFIGS = [
    # CURRENT (baseline)
    {'name': 'Current_Dynamic_SL10', 'top': 8, 'vol': 40, 'sl': -10.0, 'mom': (0.3, 0.4, 0.3), 'dyn': True},
    
    # PROVEN WINNERS from previous backtest
    {'name': 'Top6_SL10', 'top': 6, 'vol': 40, 'sl': -10.0, 'mom': (0.3, 0.4, 0.3), 'dyn': False},
    {'name': 'Tighter_SL8', 'top': 8, 'vol': 40, 'sl': -8.0, 'mom': (0.3, 0.4, 0.3), 'dyn': False},
    
    # NEW COMBINATIONS (untested)
    {'name': 'Top6_SL8_Hybrid', 'top': 6, 'vol': 40, 'sl': -8.0, 'mom': (0.3, 0.4, 0.3), 'dyn': False},
    {'name': 'Top6_Dynamic_SL8', 'top': 6, 'vol': 40, 'sl': -8.0, 'mom': (0.3, 0.4, 0.3), 'dyn': True},
    {'name': 'Top5_SL8_Ultra', 'top': 5, 'vol': 40, 'sl': -8.0, 'mom': (0.3, 0.4, 0.3), 'dyn': False},
    {'name': 'Top7_SL9', 'top': 7, 'vol': 40, 'sl': -9.0, 'mom': (0.3, 0.4, 0.3), 'dyn': False},
    {'name': 'Top6_SL10_Dynamic', 'top': 6, 'vol': 40, 'sl': -10.0, 'mom': (0.3, 0.4, 0.3), 'dyn': True},
]

if __name__ == '__main__':
    START_DATE = '2016-01-01'
    END_DATE = '2026-01-02'
    
    print("=" * 100)
    print("TESTING STRATEGY IMPROVEMENTS")
    print("=" * 100)
    print(f"\nLoading {len(TICKERS)} stocks...")
    
    prices = fetch_history(TICKERS, START_DATE, END_DATE)
    
    if prices.empty:
        print("ERROR: No price data!")
        exit(1)
    
    print(f"Loaded {len(prices.columns)} stocks with sufficient data")
    print(f"\nRunning backtest from {START_DATE} to {END_DATE}...")
    print(f"Testing {len(CONFIGS)} configurations...\n")
    
    results = []
    
    for config in CONFIGS:
        print(f"Testing {config['name']}...", end=' ')
        
        result = run_backtest(
            prices, START_DATE, END_DATE,
            config['top'], config['vol'], config['sl'],
            config['mom'], dynamic_sizing=config['dyn']
        )
        
        if result:
            results.append({
                'Name': config['name'],
                'Top': config['top'],
                'SL%': config['sl'],
                'Dyn': 'Y' if config['dyn'] else 'N',
                'CAGR%': result['cagr'],
                'Sharpe': result['sharpe'],
                'MaxDD%': result['max_dd'],
            })
            print(f"✓ CAGR: {result['cagr']:.2f}% | Sharpe: {result['sharpe']:.2f} | MaxDD: {result['max_dd']:.2f}%")
        else:
            print("✗ Failed")
    
    print("\n" + "=" * 100)
    print("RESULTS RANKED BY SHARPE RATIO")
    print("=" * 100)
    
    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values('Sharpe', ascending=False)
    
    print(df_results.to_string(index=False))
    
    print("\n" + "=" * 100)
    print("BEST STRATEGIES BY METRIC")
    print("=" * 100)
    
    best_sharpe = df_results.iloc[0]
    best_cagr = df_results.loc[df_results['CAGR%'].idxmax()]
    best_dd = df_results.loc[df_results['MaxDD%'].idxmax()]
    
    print(f"\n🏆 Best Sharpe: {best_sharpe['Name']}")
    print(f"   CAGR: {best_sharpe['CAGR%']:.2f}% | Sharpe: {best_sharpe['Sharpe']:.2f} | MaxDD: {best_sharpe['MaxDD%']:.2f}%")
    
    print(f"\n💰 Best CAGR: {best_cagr['Name']}")
    print(f"   CAGR: {best_cagr['CAGR%']:.2f}% | Sharpe: {best_cagr['Sharpe']:.2f} | MaxDD: {best_cagr['MaxDD%']:.2f}%")
    
    print(f"\n🛡️  Best Risk: {best_dd['Name']}")
    print(f"   CAGR: {best_dd['CAGR%']:.2f}% | Sharpe: {best_dd['Sharpe']:.2f} | MaxDD: {best_dd['MaxDD%']:.2f}%")
    
    # Compare to current
    current = df_results[df_results['Name'] == 'Current_Dynamic_SL10'].iloc[0]
    winner = df_results.iloc[0]
    
    print("\n" + "=" * 100)
    print("IMPROVEMENT ANALYSIS")
    print("=" * 100)
    
    if winner['Name'] != 'Current_Dynamic_SL10':
        sharpe_improvement = ((winner['Sharpe'] - current['Sharpe']) / current['Sharpe']) * 100
        cagr_improvement = winner['CAGR%'] - current['CAGR%']
        dd_improvement = winner['MaxDD%'] - current['MaxDD%']
        
        print(f"\n✅ WINNER: {winner['Name']}")
        print(f"   Sharpe improvement: {sharpe_improvement:+.1f}%")
        print(f"   CAGR improvement: {cagr_improvement:+.2f}%")
        print(f"   MaxDD improvement: {dd_improvement:+.2f}%")
        
        print(f"\n📊 Configuration:")
        print(f"   Top stocks: {int(winner['Top'])}")
        print(f"   Stop-loss: {winner['SL%']:.1f}%")
        print(f"   Dynamic sizing: {winner['Dyn']}")
    else:
        print("\n✓ Current strategy is already optimal!")
    
    # Save report
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    report_path = f"reports/improvements-{timestamp}.txt"
    
    with open(report_path, 'w') as f:
        f.write("STRATEGY IMPROVEMENT TESTING\n")
        f.write("=" * 100 + "\n\n")
        f.write(f"Period: {START_DATE} to {END_DATE}\n")
        f.write(f"Universe: {len(prices.columns)} stocks\n\n")
        f.write(df_results.to_string(index=False))
        f.write(f"\n\nBest Strategy: {winner['Name']}\n")
        f.write(f"CAGR: {winner['CAGR%']:.2f}% | Sharpe: {winner['Sharpe']:.2f} | MaxDD: {winner['MaxDD%']:.2f}%\n")
    
    print(f"\n✓ Report saved to {report_path}")
