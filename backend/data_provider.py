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

# Global cache for quotes
_quote_cache: dict[str, dict[str, Any]] = {}
_cache_time: datetime = datetime(1970, 1, 1, tzinfo=TZ)

class DataProvider:
    """Base interface for market data providers."""
    def get_quotes(self, symbols: list[str], force_refresh: bool = False) -> dict[str, dict[str, Any]]:
        """Return {symbol: {last_price, today_volume, today_open, prev_high, today_high, ask_price, sparkline}}"""
        global _quote_cache, _cache_time
        now = datetime.now(TZ)
        if not force_refresh and (now - _cache_time).total_seconds() < 5:
            return _quote_cache
            
        data = self._fetch_quotes(symbols)
        if data:
            _quote_cache.update(data)
            _cache_time = now
        return _quote_cache

    def _fetch_quotes(self, symbols: list[str]) -> dict[str, dict[str, Any]]:
        raise NotImplementedError

    def get_recent_m1_history(self, symbols: list[str], days: int = 2) -> dict[str, dict[datetime, int]]:
        """Return {symbol: {datetime: volume}} for the last `days` days of 1-minute bars."""
        raise NotImplementedError

class YahooProvider(DataProvider):
    """Fallback provider using yfinance. 15-min delayed."""
    def _fetch_quotes(self, symbols: list[str]) -> dict[str, dict[str, Any]]:
        results = {}
        try:
            # We use Tickers for efficient snapshot fetching
            tickers_str = " ".join([f"{s}.BK" for s in symbols])
            tickers = yf.Tickers(tickers_str)
            
            # We also need sparkline (5d closes)
            history = yf.download(tickers_str, period="5d", interval="1d", group_by="ticker", progress=False, threads=True)
            
            for s in symbols:
                t = f"{s}.BK"
                if t not in tickers.tickers: continue
                info = tickers.tickers[t].info
                
                # Extract Sparkline
                sparkline = []
                if not history.empty:
                    try:
                        h = history[t] if len(symbols) > 1 else history
                        sparkline = h["Close"].dropna().tail(5).tolist()
                    except: pass

                results[s] = {
                    "last_price": info.get("currentPrice") or info.get("regularMarketPrice", 0.0),
                    "today_volume": info.get("regularMarketVolume", 0),
                    "today_open": info.get("regularMarketOpen", 0.0),
                    "prev_high": 0.0, # Will be set from history below
                    "today_high": info.get("dayHigh", 0.0),
                    "ask_price": info.get("ask", 0.0) or info.get("regularMarketPrice", 0.0),
                    "change_pct": info.get("regularMarketChangePercent", 0.0),
                    "sparkline": sparkline
                }
                
                # Get prev_high from history if available
                if len(sparkline) >= 2:
                    results[s]["prev_high"] = float(history[t]["High"].iloc[-2]) if len(symbols) > 1 else float(history["High"].iloc[-2])

        except Exception as e:
            logger.error(f"YahooProvider quotes error: {e}")
            
        return results

    def get_recent_m1_history(self, symbols: list[str], days: int = 2) -> dict[str, dict[datetime, int]]:
        """Fetch 1m bars for recent days using Yahoo Finance."""
        results = {}
        try:
            # We fetch up to 5 days to ensure we cross weekends if needed
            fetch_days = max(days, 5)
            data = yf.download(
                [f"{s}.BK" for s in symbols],
                period=f"{fetch_days}d",
                interval="1m",
                group_by="ticker",
                progress=False
            )
            for s in symbols:
                ticker = f"{s}.BK"
                if ticker not in data: continue
                df = data[ticker].dropna(subset=['Volume'])
                history_dict = {}
                for ts, row in df.iterrows():
                    if ts.tzinfo is None:
                        dt = TZ.localize(ts.to_pydatetime())
                    else:
                        dt = ts.to_pydatetime().astimezone(TZ)
                    history_dict[dt] = int(row["Volume"])
                results[s] = history_dict
        except Exception as e:
            logger.error(f"YahooProvider history error: {e}")
        return results

class MT5Provider(DataProvider):
    """Primary provider using MetaTrader 5 Terminal. Real-time."""
    def __init__(self):
        self.suffix = os.getenv("MT5_SUFFIX", "") # e.g. .SET, .BK

    def _get_mt5_symbol(self, s: str) -> str:
        return f"{s}{self.suffix}"

    def _fetch_quotes(self, symbols: list[str]) -> dict[str, dict[str, Any]]:
        if not mt5 or not mt5.initialize():
            return {}
        
        results = {}
        for s in symbols:
            m_sym = self._get_mt5_symbol(s)
            tick = mt5.symbol_info_tick(m_sym)
            info = mt5.symbol_info(m_sym)
            
            if tick and info:
                # Fetch 5-day daily closes for sparkline
                rates = mt5.copy_rates_from_pos(m_sym, mt5.TIMEFRAME_D1, 0, 5)
                sparkline = [float(r.close) for r in rates] if rates is not None else []
                prev_high = float(rates[-2].high) if rates is not None and len(rates) >= 2 else 0.0

                results[s] = {
                    "last_price": tick.last,
                    "today_volume": info.volume_real if hasattr(info, 'volume_real') else info.volume,
                    "today_open": info.session_open,
                    "prev_high": prev_high,
                    "today_high": info.session_price_high,
                    "ask_price": tick.ask,
                    "change_pct": (tick.last - info.price_prev_close) / info.price_prev_close * 100.0 if info.price_prev_close > 0 else 0.0,
                    "sparkline": sparkline
                }
        return results

    def get_recent_m1_history(self, symbols: list[str], days: int = 2) -> dict[str, dict[datetime, int]]:
        """Fetch M1 bars for recent days using MT5."""
        if not mt5 or not mt5.initialize():
            return {}
        
        results = {}
        # 1 day is approx 1440 minutes max
        bars_to_fetch = 1440 * days
        for s in symbols:
            m_sym = self._get_mt5_symbol(s)
            rates = mt5.copy_rates_from_pos(m_sym, mt5.TIMEFRAME_M1, 0, bars_to_fetch)
            if rates is not None and len(rates) > 0:
                history_dict = {}
                for r in rates:
                    try:
                        # MT5 times are usually broker time, we convert from timestamp
                        dt = datetime.fromtimestamp(r.time, TZ)
                        # We use real_volume if available, else tick_volume
                        vol = int(r.real_volume) if hasattr(r, 'real_volume') and r.real_volume > 0 else int(r.tick_volume)
                        history_dict[dt] = vol
                    except Exception:
                        pass
                results[s] = history_dict
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
