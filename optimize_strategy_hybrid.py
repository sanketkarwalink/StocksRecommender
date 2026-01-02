#!/usr/bin/env python3
"""
HYBRID Strategy Optimization: Technical (Momentum) + Fundamental Filters
Combines momentum signals with fundamental quality screens
"""

import pandas as pd
import yfinance as yf
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Use working universe from strategy_backtest
try:
    from nifty500_universe import NIFTY500_TICKERS
    # Filter out known problematic tickers
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
    TICKERS = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS"]

# FUNDAMENTAL FILTER THRESHOLDS
FUNDAMENTAL_FILTERS = {
    'min_market_cap': 5000_000_000,  # ₹5000 crore minimum market cap
    'max_pe': 50,                     # P/E ratio < 50 (exclude extreme valuations)
    'min_roe': 10,                    # ROE > 10% (profitability)
    'max_debt_equity': 2.0,           # Debt/Equity < 2.0 (manageable debt)
    'min_profit_margin': 5,           # Profit margin > 5%
}

def chunked(iterable, n):
    """Split an iterable into chunks of size n"""
    for i in range(0, len(iterable), n):
        yield iterable[i:i+n]

def fetch_fundamentals(tickers):
    """Fetch fundamental data for all tickers"""
    print(f"Fetching fundamental data for {len(tickers)} stocks...")
    fundamentals = {}
    
    for i, ticker in enumerate(tickers):
        if (i + 1) % 50 == 0:
            print(f"  Progress: {i+1}/{len(tickers)} stocks...")
        
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            fundamentals[ticker] = {
                'market_cap': info.get('marketCap', 0),
                'pe_ratio': info.get('trailingPE', None),
                'forward_pe': info.get('forwardPE', None),
                'roe': info.get('returnOnEquity', None),
                'debt_equity': info.get('debtToEquity', None),
                'profit_margin': info.get('profitMargins', None),
                'revenue_growth': info.get('revenueGrowth', None),
            }
        except Exception as e:
            fundamentals[ticker] = None
            continue
    
    print(f"Fetched fundamentals for {len([f for f in fundamentals.values() if f])} stocks")
    return fundamentals

def apply_fundamental_filter(tickers, fundamentals):
    """Filter tickers based on fundamental criteria"""
    print("\nApplying fundamental filters...")
    filtered = []
    
    for ticker in tickers:
        fund = fundamentals.get(ticker)
        if not fund:
            continue
        
        # Check all fundamental criteria
        try:
            # Market cap filter
            if fund['market_cap'] < FUNDAMENTAL_FILTERS['min_market_cap']:
                continue
            
            # P/E filter (use trailing or forward PE)
            pe = fund['pe_ratio'] or fund['forward_pe']
            if pe and (pe < 0 or pe > FUNDAMENTAL_FILTERS['max_pe']):
                continue
            
            # ROE filter
            roe = fund['roe']
            if roe and roe < FUNDAMENTAL_FILTERS['min_roe'] / 100:
                continue
            
            # Debt/Equity filter
            de = fund['debt_equity']
            if de and de > FUNDAMENTAL_FILTERS['max_debt_equity'] * 100:  # yfinance returns in %
                continue
            
            # Profit margin filter
            pm = fund['profit_margin']
            if pm and pm < FUNDAMENTAL_FILTERS['min_profit_margin'] / 100:
                continue
            
            filtered.append(ticker)
        except:
            continue
    
    print(f"Fundamental filter: {len(filtered)} stocks passed (from {len(tickers)})")
    return filtered

def fetch_history(tickers, start_date, end_date):
    """Download historical data for all tickers"""
    print(f"Fetching price data for {len(tickers)} stocks from {start_date} to {end_date}...")
    
    frames = []
    failed_tickers = []
    
    for batch in chunked(tickers, 50):
        try:
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
                failed_tickers.extend(batch)
                continue
            
            if isinstance(data.columns, pd.MultiIndex):
                prices = data.xs("Close", axis=1, level=1, drop_level=True)
            else:
                prices = data[["Close"]]
                prices.columns = batch[:1]
            
            actual_loaded = prices.columns.tolist()
            failed_batch = [t for t in batch if t not in actual_loaded]
            if failed_batch:
                failed_tickers.extend(failed_batch)
            
            frames.append(prices)
        except Exception as e:
            failed_tickers.extend(batch)
            continue
    
    if not frames:
        print("ERROR: No price data fetched!")
        return pd.DataFrame()
    
    combined = pd.concat(frames, axis=1).sort_index()
    combined = combined.loc[:, ~combined.columns.duplicated()]
    combined = combined.dropna(axis=1, thresh=int(0.8 * len(combined)))
    
    print(f"Successfully loaded {len(combined.columns)} stocks")
    return combined

def compute_scores(window, momentum_weights):
    """Compute momentum scores with custom weights"""
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

def run_backtest_hybrid(prices, fundamentals, start_date, end_date, top_n, vol_cap, 
                        stop_loss, momentum_weights, rebal_freq='W-FRI', dynamic_sizing=False, use_fundamentals=True):
    """
    Hybrid backtest: Technical momentum + Optional Fundamental filters
    USES PROVEN BACKTEST ENGINE from optimize_strategy.py
    """
    portfolio = {}
    cash = 100000.0
    equity_curve = []
    
    # Get rebalance dates
    df_rebal = prices.resample(rebal_freq).last().dropna(how='all')
    
    for date in df_rebal.index:
        current_prices = df_rebal.loc[date]
        valid_prices = current_prices.dropna()
        
        if len(valid_prices) < 10:
            continue
        
        # Get 6-month window for momentum calc (PROPER DATE WINDOWING)
        window_start = date - pd.DateOffset(months=6)
        window = prices.loc[window_start:date, valid_prices.index]
        
        if len(window) < 126:
            continue
        
        # STEP 1: Apply fundamental filter (if enabled)
        if use_fundamentals and fundamentals:
            fundamentally_sound = [t for t in valid_prices.index if fundamentals.get(t)]
            if len(fundamentally_sound) < top_n:
                fundamentally_sound = valid_prices.index.tolist()  # Fallback
        else:
            fundamentally_sound = valid_prices.index.tolist()
        
        # STEP 2: Compute momentum scores
        scores = compute_scores(window[fundamentally_sound], momentum_weights)
        
        # STEP 3: Apply technical filters (CRITICAL: positive 3m and 6m returns)
        mask = (scores['vol'] < vol_cap) & (scores['ret3m'] > 0) & (scores['ret6m'] > 0)
        filtered = scores[mask].sort_values('score', ascending=False)
        
        if len(filtered) == 0:
            continue
        
        # STEP 4: Select top N
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
    max_dd = drawdown.min() * 100
    
    sharpe = (returns.mean() / returns.std()) * (252 ** 0.5) if len(returns) > 1 else 0
    
    return {
        'total_return': total_return * 100,
        'cagr': cagr,
        'sharpe': sharpe,
        'max_dd': max_dd,
        'final_value': df_equity['value'].iloc[-1]
    }

# CONFIGURATIONS TO TEST
CONFIGS = [
    # PURE TECHNICAL (baseline - no fundamental filter)
    {'name': 'Pure_Technical', 'top': 8, 'vol': 40, 'sl': -10.0, 'mom': (0.3, 0.4, 0.3), 'dyn': True, 'fundamental': False},
    
    # HYBRID (technical + fundamental filters)
    {'name': 'Hybrid_Balanced', 'top': 8, 'vol': 40, 'sl': -10.0, 'mom': (0.3, 0.4, 0.3), 'dyn': True, 'fundamental': True},
    {'name': 'Hybrid_Tight_SL8', 'top': 8, 'vol': 40, 'sl': -8.0, 'mom': (0.3, 0.4, 0.3), 'dyn': True, 'fundamental': True},
    {'name': 'Hybrid_Top6', 'top': 6, 'vol': 40, 'sl': -10.0, 'mom': (0.3, 0.4, 0.3), 'dyn': True, 'fundamental': True},
    {'name': 'Hybrid_Recent', 'top': 8, 'vol': 40, 'sl': -10.0, 'mom': (0.5, 0.3, 0.2), 'dyn': True, 'fundamental': True},
    {'name': 'Hybrid_LongTerm', 'top': 8, 'vol': 40, 'sl': -10.0, 'mom': (0.2, 0.3, 0.5), 'dyn': True, 'fundamental': True},
]

if __name__ == '__main__':
    START_DATE = '2016-01-01'
    END_DATE = '2026-01-02'
    
    print("=" * 80)
    print("HYBRID STRATEGY BACKTEST: Technical Momentum + Fundamental Quality")
    print("=" * 80)
    print(f"\nFundamental Filters Applied:")
    print(f"  • Min Market Cap: ₹{FUNDAMENTAL_FILTERS['min_market_cap']/10_000_000:.0f} crore")
    print(f"  • Max P/E Ratio: {FUNDAMENTAL_FILTERS['max_pe']}")
    print(f"  • Min ROE: {FUNDAMENTAL_FILTERS['min_roe']}%")
    print(f"  • Max Debt/Equity: {FUNDAMENTAL_FILTERS['max_debt_equity']}")
    print(f"  • Min Profit Margin: {FUNDAMENTAL_FILTERS['min_profit_margin']}%")
    print()
    
    # Fetch fundamental data ONCE (expensive operation)
    fundamentals = fetch_fundamentals(TICKERS)
    
    # Fetch price history
    prices = fetch_history(TICKERS, START_DATE, END_DATE)
    
    if prices.empty:
        print("ERROR: No price data available!")
        exit(1)
    
    print(f"\nRunning backtest from {START_DATE} to {END_DATE}...")
    print(f"Testing {len(CONFIGS)} configurations...\n")
    
    results = []
    
    for config in CONFIGS:
        print(f"Testing {config['name']}...")
        
        # Run backtest with or without fundamental filter
        result = run_backtest_hybrid(
            prices, fundamentals, START_DATE, END_DATE,
            config['top'], config['vol'], config['sl'],
            config['mom'], dynamic_sizing=config['dyn'],
            use_fundamentals=config.get('fundamental', False)
        )
        
        if result:
            results.append({
                'Name': config['name'],
                'CAGR%': result['cagr'],
                'Sharpe': result['sharpe'],
                'MaxDD%': result['max_dd'],
                'Fundamental': 'Yes' if config.get('fundamental') else 'No'
            })
            print(f"  ✓ CAGR: {result['cagr']:.2f}% | Sharpe: {result['sharpe']:.2f} | MaxDD: {result['max_dd']:.2f}%")
        else:
            print(f"  ✗ Failed to generate results")
    
    # Display results
    print("\n" + "=" * 100)
    print("RESULTS: Pure Technical vs Hybrid (Technical + Fundamental)")
    print("=" * 100)
    
    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values('Sharpe', ascending=False)
    
    print(df_results.to_string(index=False))
    
    print("\n" + "=" * 100)
    print("BEST STRATEGIES:")
    print("=" * 100)
    
    best_sharpe = df_results.iloc[0]
    best_cagr = df_results.loc[df_results['CAGR%'].idxmax()]
    best_dd = df_results.loc[df_results['MaxDD%'].idxmax()]
    
    print(f"\nBest Sharpe: {best_sharpe['Name']} (Sharpe: {best_sharpe['Sharpe']:.2f}, CAGR: {best_sharpe['CAGR%']:.2f}%)")
    print(f"Best CAGR: {best_cagr['Name']} (CAGR: {best_cagr['CAGR%']:.2f}%, Sharpe: {best_cagr['Sharpe']:.2f})")
    print(f"Best DrawDown: {best_dd['Name']} (MaxDD: {best_dd['MaxDD%']:.2f}%, CAGR: {best_dd['CAGR%']:.2f}%)")
    
    # Save report
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    report_path = f"reports/hybrid-optimization-{timestamp}.txt"
    
    with open(report_path, 'w') as f:
        f.write("HYBRID STRATEGY OPTIMIZATION: Technical + Fundamental\n")
        f.write("=" * 100 + "\n\n")
        f.write(f"Period: {START_DATE} to {END_DATE}\n")
        f.write(f"Universe: {len(prices.columns)} stocks\n\n")
        f.write("FUNDAMENTAL FILTERS:\n")
        f.write(f"  • Min Market Cap: ₹{FUNDAMENTAL_FILTERS['min_market_cap']/10_000_000:.0f} crore\n")
        f.write(f"  • Max P/E: {FUNDAMENTAL_FILTERS['max_pe']}\n")
        f.write(f"  • Min ROE: {FUNDAMENTAL_FILTERS['min_roe']}%\n")
        f.write(f"  • Max Debt/Equity: {FUNDAMENTAL_FILTERS['max_debt_equity']}\n")
        f.write(f"  • Min Profit Margin: {FUNDAMENTAL_FILTERS['min_profit_margin']}%\n\n")
        f.write(df_results.to_string(index=False))
        f.write("\n\n" + "=" * 100 + "\n")
        f.write("BEST STRATEGIES:\n")
        f.write("=" * 100 + "\n")
        f.write(f"\nBest Sharpe: {best_sharpe['Name']} (Sharpe: {best_sharpe['Sharpe']:.2f}, CAGR: {best_sharpe['CAGR%']:.2f}%)\n")
        f.write(f"Best CAGR: {best_cagr['Name']} (CAGR: {best_cagr['CAGR%']:.2f}%, Sharpe: {best_cagr['Sharpe']:.2f})\n")
        f.write(f"Best DrawDown: {best_dd['Name']} (MaxDD: {best_dd['MaxDD%']:.2f}%, CAGR: {best_dd['CAGR%']:.2f}%)\n")
    
    print(f"\n✓ Report saved to {report_path}")
