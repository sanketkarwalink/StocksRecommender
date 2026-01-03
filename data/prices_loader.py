from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable

import pandas as pd
import yfinance as yf

from data.prices import TrendInputs


def _rsi(series: pd.Series, period: int = 14) -> float:
    delta = series.diff().dropna()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    gain_last = float(gain.iloc[-1])
    loss_last = float(loss.iloc[-1])
    if loss_last == 0:
        return 50.0
    rs = gain_last / loss_last
    return 100 - (100 / (1 + rs))


def _scalar(series_val) -> float:
    try:
        return float(series_val.item())
    except Exception:
        return float(series_val)


def fetch_trend_inputs(tickers: Iterable[str], days: int = 260) -> Dict[str, TrendInputs]:
    tickers = list(tickers)
    if not tickers:
        return {}

    end = datetime.utcnow()
    start = end - timedelta(days=days)
    data = yf.download(tickers, start=start, end=end, interval="1d", auto_adjust=True, progress=False, group_by="ticker")

    trend_map: Dict[str, TrendInputs] = {}

    # Handle multiindex vs single
    for ticker in tickers:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                close = data[ticker]["Close"].dropna()
            else:
                # Single ticker case
                close = data["Close"].dropna()
            if close.empty or len(close) < 200:
                continue
            price_last = _scalar(close.iloc[-1])
            price_63 = _scalar(close.iloc[-63]) if len(close) >= 63 else price_last
            price_126 = _scalar(close.iloc[-126]) if len(close) >= 126 else price_last
            price = float(price_last)
            sma50 = float(_scalar(close.rolling(50).mean().iloc[-1]))
            sma200 = float(_scalar(close.rolling(200).mean().iloc[-1]))
            ret_3m = (price_last / price_63 - 1) * 100 if len(close) >= 63 else 0.0
            ret_6m = (price_last / price_126 - 1) * 100 if len(close) >= 126 else 0.0
            rsi14 = float(_rsi(close, 14))
            vol20 = float(_scalar(close.pct_change().rolling(20).std().iloc[-1]) * (252 ** 0.5) * 100)
            trend_map[ticker] = TrendInputs(
                price=price,
                sma50=sma50,
                sma200=sma200,
                return_3m=ret_3m,
                return_6m=ret_6m,
                rsi14=rsi14,
                vol20=vol20,
            )
        except Exception:
            continue
    return trend_map


def fetch_nifty_inputs(symbol: str = "^NSEI", days: int = 260) -> TrendInputs | None:
    data = yf.download(symbol, period=f"{days}d", interval="1d", auto_adjust=True, progress=False)
    if data.empty or len(data) < 200:
        return None
    close = data["Close"].dropna()
    price_last = _scalar(close.iloc[-1])
    price_63 = _scalar(close.iloc[-63]) if len(close) >= 63 else price_last
    price_126 = _scalar(close.iloc[-126]) if len(close) >= 126 else price_last
    price = float(price_last)
    sma50 = float(_scalar(close.rolling(50).mean().iloc[-1]))
    sma200 = float(_scalar(close.rolling(200).mean().iloc[-1]))
    ret_3m = (price_last / price_63 - 1) * 100 if len(close) >= 63 else 0.0
    ret_6m = (price_last / price_126 - 1) * 100 if len(close) >= 126 else 0.0
    rsi14 = float(_rsi(close, 14))
    vol20 = float(_scalar(close.pct_change().rolling(20).std().iloc[-1]) * (252 ** 0.5) * 100)
    return TrendInputs(price=price, sma50=sma50, sma200=sma200, return_3m=ret_3m, return_6m=ret_6m, rsi14=rsi14, vol20=vol20)
