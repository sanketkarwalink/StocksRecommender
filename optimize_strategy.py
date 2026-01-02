#!/usr/bin/env python3
"""
Enhanced Strategy Optimization
Tests multiple strategy dimensions to maximize returns and minimize drawdowns
"""

import pandas as pd
import yfinance as yf
from datetime import datetime

# Use working universe from strategy_backtest
try:
    from nifty500_universe import NIFTY500_TICKERS
    # Filter out known problematic tickers
    PROBLEMATIC = {'CEAT.NS', 'PVR.NS', 'EQUITAS.NS', 'MINDTREE.NS', 'DRREDDYS.NS', 
                   'INOXLEISUR.NS', 'JSW.NS', 'ALEMBICPH.NS', 'AARTI.NS', 'ZOMATO.NS',
                   'UJJIVAN.NS', 'DCB.NS', 'CARTRADETECH.NS', 'CADILAHC.NS', 'L&TFH.NS',
                   'VARUN.NS', 'ABBOTINDIA.NS', 'PHOENIXLTD.NS'}
    TICKERS = [t for t in NIFTY500_TICKERS if t not in PROBLEMATIC]
except:
    # Fallback to smaller working universe
    TICKERS = [
        "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
        "KOTAKBANK.NS", "SBIN.NS", "AXISBANK.NS", "BAJFINANCE.NS", "BAJAJFINSV.NS",
        "HCLTECH.NS", "WIPRO.NS", "TECHM.NS", "LT.NS", "ASIANPAINT.NS",
        "HINDUNILVR.NS", "ITC.NS", "TITAN.NS", "MARUTI.NS", "M&M.NS",
        "EICHERMOT.NS", "SUNPHARMA.NS", "CIPLA.NS", "DRREDDY.NS", "APOLLOHOSP.NS",
        "DIVISLAB.NS", "ADANIENT.NS", "ADANIPORTS.NS", "POWERGRID.NS", "NTPC.NS",
        "TATAPOWER.NS", "ONGC.NS", "BPCL.NS", "IOC.NS", "COALINDIA.NS",
        "ULTRACEMCO.NS", "GRASIM.NS", "JSWSTEEL.NS", "TATASTEEL.NS", "HINDALCO.NS",
        "BHARTIARTL.NS", "VEDL.NS", "NESTLEIND.NS", "BRITANNIA.NS", "DABUR.NS",
        "GODREJCP.NS", "MARICO.NS", "INDUSINDBK.NS", "BAJAJ-AUTO.NS", "HEROMOTOCO.NS",
        "TVSMOTOR.NS", "ASHOKLEY.NS", "TATACOMM.NS", "TATACONSUM.NS", "TATAMOTORS.NS"
    ]

def chunked(iterable, n):
    """Split an iterable into chunks of size n"""
    for i in range(0, len(iterable), n):
        yield iterable[i:i+n]

def fetch_history(tickers, start_date, end_date):
    """Download historical data for all tickers - using proven strategy_backtest approach"""
    print(f"Fetching data for {len(tickers)} stocks from {start_date} to {end_date}...")
    
    frames = []
    for batch in chunked(tickers, 40):
        data = yf.download(
            batch,
            start=start_date,
            end=end_date,
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
        print("ERROR: No price data fetched!")
        return pd.DataFrame()
    
    combined = pd.concat(frames, axis=1).sort_index()
    combined = combined.loc[:, ~combined.columns.duplicated()]
    combined = combined.dropna(axis=1, thresh=int(0.8 * len(combined)))
    
    print(f"Successfully loaded {len(combined.columns)} stocks")
    return combined

def compute_scores(window, momentum_weights):
    """
    Compute momentum scores with custom weights
    momentum_weights: tuple of (w1m, w3m, w6m)
    """
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

def run_backtest_enhanced(prices, start_date, end_date, top_n, vol_cap, stop_loss, 
                         momentum_weights, rebal_freq='W-FRI', dynamic_sizing=False):
    """
    Enhanced backtest with more parameters
    
    Args:
        dynamic_sizing: if True, weight by momentum score strength
        stop_loss: negative percentage for stop-loss (e.g., -10.0)
    """
    df_rebal = prices.resample(rebal_freq).last().dropna(how='all')
    
    portfolio = {}
    cash = 100000.0
    equity_curve = []
    
    for i, date in enumerate(df_rebal.index):
        current_prices = df_rebal.loc[date]
        valid_prices = current_prices.dropna()
        
        if len(valid_prices) < 10:
            continue
        
        # Get 6-month window for momentum calc
        window_start = date - pd.DateOffset(months=6)
        window = prices.loc[window_start:date, valid_prices.index]
        
        if len(window) < 126:
            continue
        
        # Compute scores with custom momentum weights
        scores = compute_scores(window, momentum_weights)
        
        # Filter: vol < vol_cap, positive 3m and 6m
        mask = (scores['vol'] < vol_cap) & (scores['ret3m'] > 0) & (scores['ret6m'] > 0)
        filtered = scores[mask].sort_values('score', ascending=False)
        
        if len(filtered) == 0:
            continue
        
        # Select top N
        picks = filtered.head(top_n)
        
        # Check stop-losses and exits
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
            
            # Stop-loss check
            pct_change = ((current_price - entry_price) / entry_price) * 100
            if pct_change <= stop_loss:
                to_sell.append(ticker)
            # Exit if not in top picks anymore
            elif ticker not in picks.index:
                to_sell.append(ticker)
        
        # Sell positions
        for ticker in to_sell:
            shares = portfolio[ticker]['shares']
            sell_price = valid_prices[ticker]
            cash += shares * sell_price
            del portfolio[ticker]
        
        # Calculate target positions
        portfolio_value = cash
        for ticker in portfolio:
            if ticker in valid_prices.index:
                portfolio_value += portfolio[ticker]['shares'] * valid_prices[ticker]
        
        # Buy new positions
        if dynamic_sizing:
            # Weight by score strength
            total_score = picks['score'].sum()
            target_weights = picks['score'] / total_score
        else:
            # Equal weight
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
        
        # Calculate total portfolio value
        total_value = cash
        for ticker in portfolio:
            if ticker in valid_prices.index:
                total_value += portfolio[ticker]['shares'] * valid_prices[ticker]
        
        equity_curve.append({'date': date, 'value': total_value})
    
    if len(equity_curve) < 2:
        return None
    
    # Calculate performance metrics
    df_equity = pd.DataFrame(equity_curve).set_index('date')
    returns = df_equity['value'].pct_change().dropna()
    
    total_return = (df_equity['value'].iloc[-1] / df_equity['value'].iloc[0]) - 1
    years = (df_equity.index[-1] - df_equity.index[0]).days / 365.25
    cagr = ((1 + total_return) ** (1 / years) - 1) * 100
    
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = drawdown.min() * 100
    
    if returns.std() > 0:
        sharpe = (returns.mean() / returns.std()) * (252 ** 0.5)
    else:
        sharpe = 0
    
    return {
        'cagr': cagr,
        'max_drawdown': max_drawdown,
        'sharpe': sharpe,
        'total_return': total_return * 100
    }

def optimize_strategy():
    """Run optimization grid"""
    START_DATE = '2019-01-01'
    END_DATE = '2026-01-02'
    
    # Use smaller high-quality universe for faster optimization
    CORE_TICKERS = [
        "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
        "KOTAKBANK.NS", "SBIN.NS", "AXISBANK.NS", "BAJFINANCE.NS", "BAJAJFINSV.NS",
        "HCLTECH.NS", "WIPRO.NS", "TECHM.NS", "LT.NS", "ASIANPAINT.NS",
        "HINDUNILVR.NS", "ITC.NS", "TITAN.NS", "MARUTI.NS", "M&M.NS",
        "EICHERMOT.NS", "SUNPHARMA.NS", "CIPLA.NS", "DRREDDY.NS", "APOLLOHOSP.NS",
        "DIVISLAB.NS", "ADANIENT.NS", "ADANIPORTS.NS", "POWERGRID.NS", "NTPC.NS",
        "TATAPOWER.NS", "ONGC.NS", "BPCL.NS", "IOC.NS", "COALINDIA.NS",
        "ULTRACEMCO.NS", "GRASIM.NS", "JSWSTEEL.NS", "TATASTEEL.NS", "HINDALCO.NS",
        "BHARTIARTL.NS", "VEDL.NS", "NESTLEIND.NS", "BRITANNIA.NS", "DABUR.NS",
        "GODREJCP.NS", "MARICO.NS", "INDUSINDBK.NS", "BAJAJ-AUTO.NS", "HEROMOTOCO.NS",
        "TVSMOTOR.NS", "ASHOKLEY.NS", "TATACOMM.NS", "TATACONSUM.NS", "TATAMOTORS.NS",
        "HAVELLS.NS", "PIDILITIND.NS", "BERGEPAINT.NS", "DMART.NS", "NAUKRI.NS",
        "ZYDUSLIFE.NS", "BIOCON.NS", "LUPIN.NS", "GLENMARK.NS", "TORNTPHARM.NS",
        "SHREECEM.NS", "AMBUJACEM.NS", "ACC.NS", "BANDHANBNK.NS", "FEDERALBNK.NS",
        "PFC.NS", "RECLTD.NS", "IRCTC.NS", "HAL.NS", "BEL.NS",
        "MPHASIS.NS", "LTF.NS", "CANBK.NS", "BANKBARODA.NS", "PNB.NS",
        "GODREJPROP.NS", "DLF.NS", "OBEROIRLTY.NS", "PRESTIGE.NS", "PHOENIXLTD.NS",
        "NAVABREXIM.NS", "TATACHEM.NS", "GNFC.NS", "DEEPAKNTR.NS", "AETHER.NS",
        "TATAELXSI.NS", "COFORGE.NS", "PERSISTENT.NS", "LTTS.NS", "OFSS.NS"
    ]
    
    # Fetch data once
    prices = fetch_history(CORE_TICKERS, START_DATE, END_DATE)
    
    # Parameter grid
    configurations = [
        # Baseline (current best)
        {'top_n': 8, 'vol_cap': 40.0, 'stop_loss': -12.0, 'momentum_weights': (0.3, 0.4, 0.3), 
         'rebal_freq': 'W-FRI', 'dynamic_sizing': False, 'name': 'Baseline'},
        
        # Tighter stop-loss variations
        {'top_n': 8, 'vol_cap': 40.0, 'stop_loss': -10.0, 'momentum_weights': (0.3, 0.4, 0.3), 
         'rebal_freq': 'W-FRI', 'dynamic_sizing': False, 'name': 'Tighter_SL_10'},
        {'top_n': 8, 'vol_cap': 40.0, 'stop_loss': -8.0, 'momentum_weights': (0.3, 0.4, 0.3), 
         'rebal_freq': 'W-FRI', 'dynamic_sizing': False, 'name': 'Tighter_SL_8'},
        
        # More weight on recent momentum
        {'top_n': 8, 'vol_cap': 40.0, 'stop_loss': -12.0, 'momentum_weights': (0.5, 0.3, 0.2), 
         'rebal_freq': 'W-FRI', 'dynamic_sizing': False, 'name': 'Recent_Focus'},
        {'top_n': 8, 'vol_cap': 40.0, 'stop_loss': -10.0, 'momentum_weights': (0.5, 0.3, 0.2), 
         'rebal_freq': 'W-FRI', 'dynamic_sizing': False, 'name': 'Recent_SL10'},
        
        # More weight on longer-term momentum
        {'top_n': 8, 'vol_cap': 40.0, 'stop_loss': -12.0, 'momentum_weights': (0.2, 0.3, 0.5), 
         'rebal_freq': 'W-FRI', 'dynamic_sizing': False, 'name': 'LongTerm_Focus'},
        
        # Dynamic position sizing (weight by score)
        {'top_n': 8, 'vol_cap': 40.0, 'stop_loss': -12.0, 'momentum_weights': (0.3, 0.4, 0.3), 
         'rebal_freq': 'W-FRI', 'dynamic_sizing': True, 'name': 'Dynamic_Sizing'},
        {'top_n': 8, 'vol_cap': 40.0, 'stop_loss': -10.0, 'momentum_weights': (0.3, 0.4, 0.3), 
         'rebal_freq': 'W-FRI', 'dynamic_sizing': True, 'name': 'Dynamic_SL10'},
        
        # Best vol_cap combos with tighter stops
        {'top_n': 6, 'vol_cap': 40.0, 'stop_loss': -10.0, 'momentum_weights': (0.3, 0.4, 0.3), 
         'rebal_freq': 'W-FRI', 'dynamic_sizing': False, 'name': 'Top6_SL10'},
        {'top_n': 10, 'vol_cap': 40.0, 'stop_loss': -10.0, 'momentum_weights': (0.3, 0.4, 0.3), 
         'rebal_freq': 'W-FRI', 'dynamic_sizing': False, 'name': 'Top10_SL10'},
        
        # Combination: recent focus + tight stop + dynamic sizing
        {'top_n': 8, 'vol_cap': 40.0, 'stop_loss': -10.0, 'momentum_weights': (0.5, 0.3, 0.2), 
         'rebal_freq': 'W-FRI', 'dynamic_sizing': True, 'name': 'Aggressive_Combo'},
        
        # Combination: balanced + very tight stop
        {'top_n': 8, 'vol_cap': 40.0, 'stop_loss': -8.0, 'momentum_weights': (0.3, 0.4, 0.3), 
         'rebal_freq': 'W-FRI', 'dynamic_sizing': True, 'name': 'VeryTight_Dynamic'},
        
        # Lower volatility with tighter stop
        {'top_n': 8, 'vol_cap': 35.0, 'stop_loss': -10.0, 'momentum_weights': (0.3, 0.4, 0.3), 
         'rebal_freq': 'W-FRI', 'dynamic_sizing': False, 'name': 'LowVol_SL10'},
        
        # More picks with tighter risk
        {'top_n': 12, 'vol_cap': 40.0, 'stop_loss': -10.0, 'momentum_weights': (0.3, 0.4, 0.3), 
         'rebal_freq': 'W-FRI', 'dynamic_sizing': False, 'name': 'Top12_SL10'},
    ]
    
    results = []
    
    for i, config in enumerate(configurations, 1):
        print(f"\nTesting {i}/{len(configurations)}: {config['name']}...")
        
        result = run_backtest_enhanced(
            prices, START_DATE, END_DATE,
            top_n=config['top_n'],
            vol_cap=config['vol_cap'],
            stop_loss=config['stop_loss'],
            momentum_weights=config['momentum_weights'],
            rebal_freq=config['rebal_freq'],
            dynamic_sizing=config['dynamic_sizing']
        )
        
        if result:
            results.append({
                'name': config['name'],
                'top_n': config['top_n'],
                'vol_cap': config['vol_cap'],
                'stop_loss': config['stop_loss'],
                'momentum': f"{config['momentum_weights'][0]:.1f}/{config['momentum_weights'][1]:.1f}/{config['momentum_weights'][2]:.1f}",
                'dynamic': 'Y' if config['dynamic_sizing'] else 'N',
                'cagr': result['cagr'],
                'max_dd': result['max_drawdown'],
                'sharpe': result['sharpe']
            })
            print(f"  CAGR: {result['cagr']:.2f}%, MaxDD: {result['max_drawdown']:.2f}%, Sharpe: {result['sharpe']:.2f}")
    
    # Sort by Sharpe ratio
    if len(results) == 0:
        print("No valid results generated!")
        return None
    
    results_df = pd.DataFrame(results).sort_values('sharpe', ascending=False)
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    output_file = f'reports/optimization-{timestamp}.txt'
    
    with open(output_file, 'w') as f:
        f.write("STRATEGY OPTIMIZATION RESULTS\n")
        f.write("=" * 120 + "\n\n")
        f.write(f"Universe: {len(prices.columns)} NIFTY 500 stocks\n")
        f.write(f"Period: {START_DATE} to {END_DATE}\n")
        f.write(f"Configurations tested: {len(results)}\n\n")
        
        f.write("RANKED BY SHARPE RATIO\n")
        f.write("-" * 120 + "\n")
        f.write(f"{'Name':<20} {'Top':<4} {'Vol':<5} {'SL%':<6} {'Momentum':<10} {'Dyn':<4} {'CAGR%':<8} {'MaxDD%':<8} {'Sharpe':<7}\n")
        f.write("-" * 120 + "\n")
        
        for _, row in results_df.iterrows():
            f.write(f"{row['name']:<20} {row['top_n']:<4} {row['vol_cap']:<5.0f} "
                   f"{row['stop_loss']:<6.1f} {row['momentum']:<10} {row['dynamic']:<4} "
                   f"{row['cagr']:<8.2f} {row['max_dd']:<8.2f} {row['sharpe']:<7.2f}\n")
        
        f.write("\n" + "=" * 120 + "\n\n")
        
        # Best by each metric
        f.write("BEST BY METRIC:\n")
        f.write("-" * 120 + "\n")
        best_sharpe = results_df.iloc[0]
        best_cagr = results_df.loc[results_df['cagr'].idxmax()]
        best_dd = results_df.loc[results_df['max_dd'].idxmax()]  # Least negative
        
        f.write(f"\nBest Sharpe: {best_sharpe['name']} (Sharpe: {best_sharpe['sharpe']:.2f}, CAGR: {best_sharpe['cagr']:.2f}%, MaxDD: {best_sharpe['max_dd']:.2f}%)\n")
        f.write(f"Best CAGR: {best_cagr['name']} (CAGR: {best_cagr['cagr']:.2f}%, MaxDD: {best_cagr['max_dd']:.2f}%, Sharpe: {best_cagr['sharpe']:.2f})\n")
        f.write(f"Best DrawDown: {best_dd['name']} (MaxDD: {best_dd['max_dd']:.2f}%, CAGR: {best_dd['cagr']:.2f}%, Sharpe: {best_dd['sharpe']:.2f})\n")
    
    print(f"\n{'='*120}")
    print(f"Results saved to {output_file}")
    print(f"{'='*120}\n")
    print(results_df.to_string(index=False))
    
    return results_df

if __name__ == '__main__':
    optimize_strategy()
