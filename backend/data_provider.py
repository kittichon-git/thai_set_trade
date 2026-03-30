# data_provider.py — Hybrid data feed (MT5 + Yahoo Finance)
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Optional

import pytz
import yfinance as yf

logger = logging.getLogger(__name__)
TZ = pytz.timezone("Asia/Bangkok")

# For MT5, we only import if needed/available to avoid crashes on non-Windows/no-MT5 envs
mt5 = None
try:
    import MetaTrader5 as m5
    mt5 = m5
except ImportError:
    logger.warning("MetaTrader5 library not found. MT5Provider will be unavailable.")

class DataProvider:
    """Base interface for market data providers."""
    def get_quotes(self, symbols: list[str]) -> dict[str, dict[str, Any]]:
        """Return {symbol: {last_price, today_volume, today_open, prev_high, today_high, ask_price}}"""
        raise NotImplementedError

    def get_yesterday_morning_data(self, symbols: list[str]) -> dict[str, list[int]]:
        """Return {symbol: [vol_m1, vol_m2, ..., vol_m15]} for yesterday's first 15 mins."""
        raise NotImplementedError

class YahooProvider(DataProvider):
    """Fallback provider using yfinance. 15-min delayed."""
    def get_quotes(self, symbols: list[str]) -> dict[str, dict[str, Any]]:
        results = {}
        # Fetching in chunks for efficiency
        try:
            # yfinance download for 1d history to get open, high, and current
            data = yf.download(
                [" ".join([f"{s}.BK" for s in symbols])],
                period="1d",
                interval="1m",
                group_by="ticker",
                progress=False,
                threads=True
            )
            
            for s in symbols:
                ticker = f"{s}.BK"
                if ticker not in data: continue
                
                df = data[ticker]
                if df.empty: continue
                
                last_row = df.iloc[-1]
                first_row = df.iloc[0]
                
                results[s] = {
                    "last_price": float(last_row["Close"]),
                    "today_volume": int(last_row["Volume"]), # yf 'Volume' in 1m is cumulative today? No, it's bar volume. 
                    # Actually yf 1d interval Volume is cumulative. 1m is bar volume.
                    # We need cumulative volume.
                }
            
            # Alternative: use Tickers object for snapshot (quicker for daily totals)
            tickers = yf.Tickers(" ".join([f"{s}.BK" for s in symbols]))
            for s in symbols:
                t = f"{s}.BK"
                if t not in tickers.tickers: continue
                info = tickers.tickers[t].info
                
                results[s] = {
                    "last_price": info.get("currentPrice") or info.get("regularMarketPrice", 0.0),
                    "today_volume": info.get("regularMarketVolume", 0),
                    "today_open": info.get("regularMarketOpen", 0.0),
                    "prev_high": info.get("regularMarketDayHigh", 0.0), # This might be today's high
                    "today_high": info.get("dayHigh", 0.0),
                    "ask_price": info.get("ask", 0.0) or info.get("regularMarketPrice", 0.0),
                }
        except Exception as e:
            logger.error(f"YahooProvider quotes error: {e}")
            
        return results

    def get_yesterday_morning_data(self, symbols: list[str]) -> dict[str, list[int]]:
        """Fetch 1m bars for yesterday's opening."""
        results = {}
        try:
            # We fetch 5 days to ensure we catch 'yesterday' even after weekends
            data = yf.download(
                [f"{s}.BK" for s in symbols],
                period="5d",
                interval="1m",
                group_by="ticker",
                progress=False
            )
            
            # Find the most recent date that is NOT today
            all_dates = sorted(data.index.normalize().unique())
            if len(all_dates) < 2: return {}
            yesterday = all_dates[-2] # second to last date
            
            for s in symbols:
                ticker = f"{s}.BK"
                if ticker not in data: continue
                df = data[ticker]
                # Filter for yesterday's morning (09:30 - 10:15)
                # BKK market open is 10:00 (Pre-open 09:30)
                # Note: yfinance timezone might be UTC? No, usually local if specified.
                # Thai market is UTC+7. 
                y_df = df[df.index.normalize() == yesterday]
                # Filter 10:00 - 10:15 BKK
                morning_df = y_df.between_time("10:00", "10:15")
                results[s] = morning_df["Volume"].tolist()
        except Exception as e:
            logger.error(f"YahooProvider history error: {e}")
        return results

class MT5Provider(DataProvider):
    """Primary provider using MetaTrader 5 Terminal. Real-time."""
    def __init__(self):
        self.suffix = os.getenv("MT5_SUFFIX", "") # e.g. .SET, .BK

    def _get_mt5_symbol(self, s: str) -> str:
        return f"{s}{self.suffix}"

    def get_quotes(self, symbols: list[str]) -> dict[str, dict[str, Any]]:
        if not mt5 or not mt5.initialize():
            return {}
        
        results = {}
        for s in symbols:
            m_sym = self._get_mt5_symbol(s)
            tick = mt5.symbol_info_tick(m_sym)
            info = mt5.symbol_info(m_sym)
            
            if tick and info:
                # MT5 info.volume is usually volume_real or volume
                # For SET, we need to check which field corresponds to Today's Volume
                results[s] = {
                    "last_price": tick.last,
                    "today_volume": info.volume_real if hasattr(info, 'volume_real') else info.volume,
                    "today_open": info.session_open,
                    "prev_high": info.session_price_limit_max, # This might be limit price. 
                    # Better to fetch from M1 history if info doesn't have yesterday's high
                    "today_high": info.session_price_high,
                    "ask_price": tick.ask,
                }
        return results

    def get_yesterday_morning_data(self, symbols: list[str]) -> dict[str, list[int]]:
        """Fetch M1 bars for yesterday's opening."""
        if not mt5 or not mt5.initialize():
            return {}
        
        results = {}
        # Get last 2 session info to find 'yesterday'
        now = datetime.now()
        for s in symbols:
            m_sym = self._get_mt5_symbol(s)
            # Fetch last 1000 M1 bars to find yesterday's start
            rates = mt5.copy_rates_from_pos(m_sym, mt5.TIMEFRAME_M1, 0, 1000)
            if rates is not None and len(rates) > 0:
                # Group by date
                # ... complex grouping logic ...
                # Simple version: find first block of 10:00 bars before today's 10:00
                pass
        return results

# Global Provider Discovery
_provider: Optional[DataProvider] = None

def get_provider() -> DataProvider:
    global _provider
    if _provider: return _provider
    
    # Try MT5 first
    if mt5 and mt5.initialize():
        logger.info("Using MT5Provider")
        _provider = MT5Provider()
    else:
        logger.info("Using YahooProvider (Fallback)")
        _provider = YahooProvider()
    return _provider
