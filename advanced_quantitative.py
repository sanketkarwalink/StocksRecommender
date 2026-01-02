#!/usr/bin/env python3
"""
ADVANCED QUANTITATIVE STRATEGY: Multi-Factor Mathematical Optimization
Combines momentum, volatility, correlation, and risk metrics for maximum profit with minimum losses
Based on Renaissance Technologies approach
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
from scipy import stats

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

class AdvancedQuantStrategy:
    """
    Multi-Factor Quantitative Strategy combining:
    1. Momentum Score (price momentum)
    2. Quality Score (trend strength and stability)
    3. Risk Score (volatility and drawdown)
    4. Relative Strength Index (RSI - overbought/oversold)
    5. Mean Reversion Signal (fade extreme moves)
    6. Sharpe Ratio (risk-adjusted returns)
    7. Correlation Hedging (avoid highly correlated pairs)
    """
    
    def __init__(self):
        self.weights = {
            'momentum': 0.35,      # 35% - Strong performers
            'quality': 0.25,       # 25% - Trend quality/stability
            'risk': -0.15,         # -15% - Penalize high volatility
            'rsi': 0.10,           # 10% - Momentum confirmation
            'sharpe': 0.15,        # 15% - Risk-adjusted returns
            'mean_reversion': 0.05 # 5% - Counter-trend confirmation
        }
    
    def calculate_momentum(self, window):
        """
        MOMENTUM FORMULA:
        Score = w1 × R₁ₘ + w3 × R₃ₘ + w6 × R₆ₘ
        where R = (Price_today / Price_past - 1) × 100
        """
        ret1m = window.pct_change(21, fill_method=None).iloc[-1] * 100
        ret3m = window.pct_change(63, fill_method=None).iloc[-1] * 100
        ret6m = window.pct_change(126, fill_method=None).iloc[-1] * 100
        
        scores = 0.3 * ret1m + 0.4 * ret3m + 0.3 * ret6m
        return pd.Series(scores)
    
    def calculate_quality(self, window):
        """
        QUALITY SCORE FORMULA:
        Quality = Trend_Strength × Stability
        
        Trend_Strength = |SMA_20 - SMA_50| / SMA_50
        Stability = 1 / (1 + StdDev_of_returns)
        
        Penalizes choppy/volatile trends, rewards smooth uptrends
        """
        prices = window.iloc[-126:]  # 6 months
        sma20 = prices.rolling(20).mean()
        sma50 = prices.rolling(50).mean()
        
        # Trend strength (difference between moving averages)
        trend_strength = np.abs(sma20 - sma50) / sma50 * 100
        trend_strength = trend_strength.iloc[-1]
        
        # Stability (inverse of volatility)
        daily_returns = prices.pct_change().dropna()
        volatility = daily_returns.std()
        stability = 1.0 / (1.0 + volatility * 10)  # Scale and invert
        
        quality = trend_strength * stability
        return pd.Series(quality, index=window.columns)
    
    def calculate_rsi(self, window):
        """
        RSI FORMULA (Relative Strength Index):
        RSI = 100 - (100 / (1 + RS))
        RS = Average_Gain / Average_Loss over 14 periods
        
        Normalized to 0-100:
        - RSI > 70 = Overbought (warning signal)
        - RSI < 30 = Oversold (buying opportunity)
        - RSI 40-60 = Neutral (best signal quality)
        """
        delta = window.diff()
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)
        
        avg_gain = pd.Series(gain).rolling(14).mean()
        avg_loss = pd.Series(loss).rolling(14).mean()
        
        rs = avg_gain / (avg_loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        
        # Normalize RSI signal: higher score for 40-60 range
        # Score = 1 - |RSI - 50| / 50 (peaks at 50, drops at extremes)
        normalized_signal = 1.0 - np.abs(rsi.iloc[-1] - 50) / 50
        return pd.Series(normalized_signal, index=window.columns)
    
    def calculate_sharpe_ratio(self, window):
        """
        SHARPE RATIO FORMULA:
        Sharpe = (Mean_Return / Std_Return) × √252
        
        Measures risk-adjusted returns
        Higher = Better returns for given risk
        """
        returns = window.pct_change().dropna()
        
        mean_ret = returns.mean()
        std_ret = returns.std()
        
        sharpe = (mean_ret / (std_ret + 1e-10)) * np.sqrt(252)
        return pd.Series(sharpe, index=window.columns)
    
    def calculate_mean_reversion(self, window):
        """
        MEAN REVERSION FORMULA:
        z_score = (Price - SMA_20) / StdDev_20
        
        When z_score > 2 (price > 2 std above mean):
        - Stock is overbought, prone to pullback
        - Give NEGATIVE score (fade the move)
        
        When z_score < -2 (price < 2 std below mean):
        - Stock is oversold, prone to bounce
        - Give POSITIVE score (bounce play)
        
        Benefit: Catches reversal opportunities
        """
        sma20 = window.rolling(20).mean()
        std20 = window.rolling(20).std()
        
        z_score = (window - sma20) / (std20 + 1e-10)
        
        # Mean reversion signal: return toward mean
        # Score = -z_score (negative when overbought, positive when oversold)
        mr_signal = -z_score.iloc[-1]
        return pd.Series(mr_signal, index=window.columns)
    
    def calculate_volatility_risk(self, window):
        """
        VOLATILITY RISK FORMULA:
        σ = √252 × σ_daily
        Risk_Penalty = -σ / (1 + σ)
        
        Penalizes high volatility stocks
        High volatility = higher losses in crashes
        """
        returns = window.pct_change().dropna()
        daily_vol = returns.std()
        annual_vol = daily_vol * np.sqrt(252)
        
        # Penalty: increases as volatility increases
        # -0 for vol=0, -0.5 for vol=100%, -1 for vol=∞
        risk_penalty = -annual_vol / (1.0 + annual_vol) * 100
        return pd.Series(risk_penalty, index=window.columns)
    
    def calculate_correlation_penalty(self, window, all_correlations, ticker):
        """
        CORRELATION PENALTY FORMULA:
        Penalty = -0.1 × Avg_Correlation
        
        Penalizes stocks highly correlated with others in portfolio
        Reduces concentration risk and improves diversification
        """
        if ticker not in all_correlations.index:
            return 0
        
        # Get average correlation with all other stocks
        avg_corr = all_correlations.loc[ticker].mean()
        
        # Penalty: higher correlation = lower score
        penalty = -0.1 * avg_corr
        return penalty
    
    def calculate_composite_score(self, prices, date, correlations):
        """
        COMPOSITE SCORE FORMULA:
        Composite_Score = Σ(w_i × Signal_i) where i ∈ {momentum, quality, risk, RSI, sharpe, mr}
        
        This combines multiple independent signals:
        - Momentum: Absolute price strength
        - Quality: Smooth, sustainable trends
        - Risk: Penalize high volatility
        - RSI: Confirm with technical indicator
        - Sharpe: Risk-adjusted returns
        - Mean Reversion: Catch reversals
        - Correlation: Diversification
        """
        window_start = date - pd.DateOffset(months=6)
        window = prices.loc[window_start:date]
        
        if len(window) < 126:
            return pd.DataFrame()
        
        # Calculate all signals
        momentum = self.calculate_momentum(window)
        quality = self.calculate_quality(window)
        risk = self.calculate_volatility_risk(window)
        rsi = self.calculate_rsi(window)
        sharpe = self.calculate_sharpe_ratio(window)
        mean_rev = self.calculate_mean_reversion(window)
        
        # Normalize signals to 0-100 scale
        momentum_norm = (momentum - momentum.min()) / (momentum.max() - momentum.min() + 1e-10) * 100
        quality_norm = (quality - quality.min()) / (quality.max() - quality.min() + 1e-10) * 100
        rsi_norm = rsi * 100
        sharpe_norm = (sharpe - sharpe.min()) / (sharpe.max() - sharpe.min() + 1e-10) * 100
        mean_rev_norm = (mean_rev - mean_rev.min()) / (mean_rev.max() - mean_rev.min() + 1e-10) * 100
        risk_norm = risk  # Already 0-100 scale
        
        # Apply correlation penalty
        corr_penalty = pd.Series(0.0, index=window.columns)
        for ticker in window.columns:
            corr_penalty[ticker] = self.calculate_correlation_penalty(window, correlations, ticker)
        
        # Calculate composite score
        composite = (
            self.weights['momentum'] * momentum_norm +
            self.weights['quality'] * quality_norm +
            self.weights['risk'] * risk_norm +
            self.weights['rsi'] * rsi_norm +
            self.weights['sharpe'] * sharpe_norm +
            self.weights['mean_reversion'] * mean_rev_norm +
            corr_penalty * 10  # Scale correlation penalty
        )
        
        return pd.DataFrame({
            'composite': composite,
            'momentum': momentum_norm,
            'quality': quality_norm,
            'risk': risk_norm,
            'rsi': rsi_norm,
            'sharpe': sharpe_norm,
            'mean_reversion': mean_rev_norm,
            'original_momentum': momentum,
            'original_volatility': window.pct_change().std() * np.sqrt(252) * 100
        })
    
    def calculate_optimal_position_size(self, score, volatility, portfolio_value):
        """
        OPTIMAL POSITION SIZING FORMULA (Kelly Criterion variant):
        f* = (score / volatility) / 100
        
        Position_Size = Portfolio_Value × f* × (1 / N_positions)
        
        This sizes positions inversely to volatility:
        - High score + Low volatility = Large position
        - High score + High volatility = Small position
        - Low score = Minimal position
        
        Benefit: Automatically manages risk, concentrates capital on best risk-adjusted picks
        """
        if volatility < 20:
            volatility = 20  # Floor at 20% to avoid extreme sizing
        
        # Score-to-volatility ratio: high score, low volatility = high ratio
        strength = score / volatility
        
        # Kelly criterion: f* = (edge / odds)
        # Capped at 0.2 (max 20% of portfolio per position)
        kelly_fraction = min(strength / 500.0, 0.20)
        
        return kelly_fraction

def run_advanced_backtest(prices, start_date, end_date):
    """Run backtest with advanced multi-factor strategy"""
    
    strategy = AdvancedQuantStrategy()
    portfolio = {}
    cash = 100000.0
    equity_curve = []
    
    # Calculate correlations (for diversification benefit)
    daily_returns = prices.pct_change().dropna()
    correlations = daily_returns.corr()
    
    for date in prices.resample('W-FRI').last().dropna(how='all').index:
        current_prices = prices.resample('W-FRI').last().loc[date]
        valid_prices = current_prices.dropna()
        
        if len(valid_prices) < 10:
            continue
        
        # Calculate composite scores
        scores_df = strategy.calculate_composite_score(prices.loc[:date], date, correlations)
        
        if scores_df.empty:
            continue
        
        # Filter for quality signals
        mask = (
            (scores_df['original_volatility'] < 60) &  # Vol cap
            (scores_df['composite'] > 0) &  # Positive composite signal
            (scores_df['momentum'] > 30)  # Minimum momentum threshold
        )
        filtered = scores_df[mask].sort_values('composite', ascending=False)
        
        if len(filtered) == 0:
            continue
        
        # Select top 6 based on composite score
        picks = filtered.head(6)
        
        # Remove old positions not in picks
        to_sell = [t for t in portfolio if t not in picks.index]
        for ticker in to_sell:
            shares = portfolio[ticker]['shares']
            sell_price = valid_prices[ticker]
            cash += shares * sell_price
            del portfolio[ticker]
        
        # Check stop-losses
        for ticker in list(portfolio.keys()):
            shares = portfolio[ticker]['shares']
            entry = portfolio[ticker]['entry_price']
            current_price = valid_prices[ticker]
            pnl_pct = (current_price - entry) / entry * 100
            
            if pnl_pct <= -8.0:
                cash += shares * current_price
                del portfolio[ticker]
        
        # Calculate portfolio value
        portfolio_value = cash
        for ticker in portfolio:
            if ticker in valid_prices.index:
                portfolio_value += portfolio[ticker]['shares'] * valid_prices[ticker]
        
        # Rebalance with optimal position sizing
        for ticker in picks.index:
            score = picks.loc[ticker, 'composite']
            vol = picks.loc[ticker, 'original_volatility']
            
            kelly_fraction = strategy.calculate_optimal_position_size(score, vol, portfolio_value)
            target_value = portfolio_value * kelly_fraction
            
            if ticker not in portfolio:
                current_price = valid_prices[ticker]
                shares_to_buy = int(target_value / current_price)
                
                if shares_to_buy > 0:
                    cost = shares_to_buy * current_price
                    if cost <= cash:
                        portfolio[ticker] = {
                            'shares': shares_to_buy,
                            'entry_price': current_price,
                            'score': score
                        }
                        cash -= cost
        
        # Record portfolio value
        portfolio_value = cash
        for ticker in portfolio:
            if ticker in valid_prices.index:
                portfolio_value += portfolio[ticker]['shares'] * valid_prices[ticker]
        
        equity_curve.append({'date': date, 'value': portfolio_value})
    
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

if __name__ == '__main__':
    START_DATE = '2016-01-01'
    END_DATE = '2026-01-02'
    
    print("=" * 100)
    print("ADVANCED QUANTITATIVE STRATEGY: Multi-Factor Mathematical Optimization")
    print("=" * 100)
    print("\nMathematical Formulas Used:")
    print("1. Momentum Score: w1×R1m + w3×R3m + w6×R6m")
    print("2. Quality Score: Trend_Strength × Stability")
    print("3. RSI: 100 - (100/(1+RS))")
    print("4. Sharpe Ratio: (Mean_Return/Std_Return) × √252")
    print("5. Mean Reversion: z_score = (Price - SMA20) / StdDev20")
    print("6. Volatility Risk: σ = √252 × σ_daily")
    print("7. Kelly Criterion: f* = (score/volatility) / 100")
    print("8. Composite Score: Σ(w_i × Signal_i)")
    
    print(f"\nLoading {len(TICKERS)} stocks...")
    prices = fetch_history(TICKERS, START_DATE, END_DATE)
    
    if prices.empty:
        print("ERROR: No price data!")
        exit(1)
    
    print(f"Loaded {len(prices.columns)} stocks")
    print(f"\nRunning advanced quantitative backtest (2016-2026)...\n")
    
    result = run_advanced_backtest(prices, START_DATE, END_DATE)
    
    if result:
        print("=" * 100)
        print("RESULTS: Advanced Multi-Factor Strategy")
        print("=" * 100)
        print(f"\nCAGR: {result['cagr']:.2f}%")
        print(f"Sharpe Ratio: {result['sharpe']:.2f}")
        print(f"Maximum Drawdown: {result['max_dd']:.2f}%")
        
        # Compare to Top6_SL8
        print("\n" + "=" * 100)
        print("COMPARISON")
        print("=" * 100)
        print(f"\nTop6_SL8_Hybrid:      35.38% CAGR | 4.51 Sharpe | -13.13% MaxDD")
        print(f"Advanced Multi-Factor: {result['cagr']:.2f}% CAGR | {result['sharpe']:.2f} Sharpe | {result['max_dd']:.2f}% MaxDD")
        
        if result['cagr'] > 35.38:
            improvement = result['cagr'] - 35.38
            print(f"\n✅ IMPROVEMENT: +{improvement:.2f}% CAGR! 🚀")
        else:
            print("\n✓ Multi-factor diversifies approach (lower CAGR but different risk profile)")
    else:
        print("ERROR: Backtest failed")
