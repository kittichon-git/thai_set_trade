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
            tickers_str = " ".join([f"{s}.BK" for s in symbols])
            # Single batch download — much faster than calling .info per ticker
            hist = yf.download(
                tickers_str, period="50d", interval="1d",
                group_by="ticker", progress=False, auto_adjust=False
            )
            if hist.empty:
                return results

            multi = len(symbols) > 1

            for s in symbols:
                try:
                    h = hist[f"{s}.BK"] if multi else hist
                    h = h.dropna(how="all")
                    if h.empty or len(h) < 1:
                        continue

                    last = h.iloc[-1]
                    prev = h.iloc[-2] if len(h) >= 2 else last

                    vols = h["Volume"].dropna().tolist()
                    avg_5d = int(sum(vols[-5:]) / len(vols[-5:])) if vols else 0
                    sparkline = [float(v) for v in h["Close"].dropna().tail(5).tolist()]

                    last_close = float(last["Close"])
                    prev_close = float(prev["Close"])
                    change_pct = ((last_close - prev_close) / prev_close * 100) if prev_close > 0 else 0.0

                    # OHLC for candlestick chart (last 6 trading days)
                    import math
                    ohlc = []
                    for idx, row in h.tail(30).iterrows():
                        try:
                            o, hi, lo, c = float(row["Open"]), float(row["High"]), float(row["Low"]), float(row["Close"])
                            v = float(row["Volume"])
                            if any(math.isnan(x) for x in [o, hi, lo, c]):
                                continue
                            ohlc.append({
                                "time": idx.strftime("%Y-%m-%d"),
                                "open": o, "high": hi, "low": lo, "close": c,
                                "volume": 0 if math.isnan(v) else int(v),
                            })
                        except Exception:
                            pass

                    results[s] = {
                        "last_price": last_close,
                        "today_volume": int(last["Volume"]) if last["Volume"] == last["Volume"] else 0,
                        "avg_5d_volume": avg_5d,
                        "today_open": float(last["Open"]),
                        "prev_high": float(prev["High"]),
                        "today_high": float(last["High"]),
                        "ask_price": last_close,
                        "change_pct": change_pct,
                        "sparkline": sparkline,
                        "ohlc": ohlc,
                    }
                except Exception as e:
                    logger.debug("[YahooProvider] %s error: %s", s, e)

        except Exception as e:
            logger.error("[YahooProvider] fatal error: %s", e)

        logger.info("[YahooProvider] fetched %d/%d symbols", len(results), len(symbols))
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
            mt5.symbol_select(m_sym, True)
            tick = mt5.symbol_info_tick(m_sym)
            info = mt5.symbol_info(m_sym)

            if not info:
                continue

            # Fetch 30-day daily bars for sparkline + OHLC
            rates = mt5.copy_rates_from_pos(m_sym, mt5.TIMEFRAME_D1, 0, 30)
            sparkline = [float(r[4]) for r in rates[-5:]] if rates is not None and len(rates) >= 1 else []
            prev_high = float(rates[-2][2]) if rates is not None and len(rates) >= 2 else 0.0
            avg_5d_volume = int(sum(r[7] if r[7] > 0 else r[5] for r in rates[-5:]) / min(5, len(rates))) if rates is not None and len(rates) > 0 else 0

            ohlc = []
            if rates is not None:
                for r in rates:
                    try:
                        dt = datetime.fromtimestamp(r[0], TZ)
                        vol = int(r[7]) if r[7] > 0 else int(r[5])
                        ohlc.append({
                            "time": dt.strftime("%Y-%m-%d"),
                            "open": float(r[1]), "high": float(r[2]),
                            "low": float(r[3]), "close": float(r[4]),
                            "volume": vol,
                        })
                    except Exception:
                        pass

            # ราคาล่าสุด: ใช้ tick.last ถ้ามี ถ้าไม่มี (ตลาดปิด) ใช้ราคาปิดล่าสุดจาก rates
            last_price = tick.last if tick and tick.last > 0 else (float(rates[-1][4]) if rates is not None and len(rates) > 0 else 0.0)
            ask_price  = tick.ask  if tick and tick.ask  > 0 else last_price
            prev_close = float(rates[-2][4]) if rates is not None and len(rates) >= 2 else 0.0
            change_pct = (last_price - prev_close) / prev_close * 100.0 if prev_close > 0 else 0.0

            today_volume = int(info.session_volume) if info.session_volume > 0 else (int(rates[-1][7]) if rates is not None and len(rates) > 0 and rates[-1][7] > 0 else int(rates[-1][5]) if rates is not None and len(rates) > 0 else 0)

            results[s] = {
                "last_price": last_price,
                "today_volume": today_volume,
                "avg_5d_volume": avg_5d_volume,
                "today_open": getattr(info, 'session_open', 0.0) or (float(rates[-1][1]) if rates is not None and len(rates) > 0 else 0.0),
                "prev_high": prev_high,
                "today_high": getattr(info, 'session_price_high', 0.0) or (float(rates[-1][2]) if rates is not None and len(rates) > 0 else 0.0),
                "ask_price": ask_price,
                "change_pct": change_pct,
                "sparkline": sparkline,
                "ohlc": ohlc,
            }
        return results

    def get_recent_m1_history(self, symbols: list[str], days: int = 2) -> dict[str, dict[datetime, int]]:
        """Fetch M1 bars for recent days using MT5."""
        if not mt5 or not mt5.initialize():
            return {}

        results = {}
        bars_to_fetch = 1440 * days
        for s in symbols:
            m_sym = self._get_mt5_symbol(s)
            mt5.symbol_select(m_sym, True)
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

    # Use MT5 only when explicitly enabled via env var
    use_mt5 = os.getenv("USE_MT5", "false").lower() == "true"
    if use_mt5 and mt5 and mt5.initialize():
        logger.info("Using MT5Provider")
        _provider = MT5Provider()
    else:
        logger.info("Using YahooProvider")
        _provider = YahooProvider()
    return _provider
