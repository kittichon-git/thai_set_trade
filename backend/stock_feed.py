# stock_feed.py — yfinance-based stock quote fetcher for DW Dashboard
# Fetches daily + intraday data for all DW underlying stocks
# Runs in asyncio.to_thread to avoid blocking the event loop
from __future__ import annotations

import asyncio
import logging
from typing import Any

import yfinance as yf
import pandas as pd

logger = logging.getLogger(__name__)

# Global cache — updated every 10s during market hours
# Structure per symbol: {last_price, change_pct, today_volume, avg_5d_volume, sparkline}
STOCK_DATA: dict[str, dict[str, Any]] = {}


def _fetch_sync(symbols: list[str]) -> dict[str, dict[str, Any]]:
    """
    Synchronous yfinance batch fetch for daily and intraday data.
    Returns a dict mapping clean symbol (without .BK) -> quote data.
    Called via asyncio.to_thread to avoid blocking the event loop.
    """
    if not symbols:
        return {}

    # Append .BK suffix for Thai SET stocks
    sym_to_bk: dict[str, str] = {}
    bk_syms: list[str] = []
    for s in symbols:
        bk = s if s.upper().endswith(".BK") else f"{s.upper()}.BK"
        sym_to_bk[s.upper()] = bk
        bk_syms.append(bk)

    tickers_str = " ".join(bk_syms)
    result: dict[str, dict[str, Any]] = {}

    # -----------------------------------------------------------------------
    # Fetch 5-day daily OHLCV for sparkline + average volume + prev close
    # -----------------------------------------------------------------------
    daily_data: pd.DataFrame | None = None
    try:
        daily_data = yf.download(
            tickers=tickers_str,
            period="5d",
            interval="1d",
            group_by="ticker",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
        logger.info("Daily fetch complete for %d symbols", len(bk_syms))
    except Exception as e:
        logger.warning("yfinance daily download error: %s", e)
        daily_data = None

    # -----------------------------------------------------------------------
    # Fetch intraday 1-min data (today's volume)
    # -----------------------------------------------------------------------
    intraday_data: pd.DataFrame | None = None
    try:
        intraday_data = yf.download(
            tickers=tickers_str,
            period="1d",
            interval="1m",
            group_by="ticker",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
        logger.info("Intraday fetch complete for %d symbols", len(bk_syms))
    except Exception as e:
        logger.warning("yfinance intraday download error: %s", e)
        intraday_data = None

    # -----------------------------------------------------------------------
    # Parse data per symbol
    # -----------------------------------------------------------------------
    is_single = len(bk_syms) == 1
    for clean_sym, bk_sym in sym_to_bk.items():
        try:
            # --- Extract daily data ---
            last_price = 0.0
            change_pct = 0.0
            avg_5d_volume = 0
            sparkline: list[float] = []

            if daily_data is not None and not daily_data.empty:
                try:
                    if is_single or not isinstance(daily_data.columns, pd.MultiIndex):
                        # Single ticker or flat DataFrame
                        sym_daily = daily_data
                    else:
                        # Multi-ticker: multi-level columns (field, symbol)
                        sym_daily = daily_data[bk_sym]

                    if not sym_daily.empty:
                        closes = sym_daily["Close"].dropna()
                        volumes = sym_daily["Volume"].dropna()

                        if len(closes) >= 1:
                            last_price = float(closes.iloc[-1])
                        if len(closes) >= 2:
                            prev_close = float(closes.iloc[-2])
                            if prev_close > 0:
                                change_pct = (last_price - prev_close) / prev_close * 100.0

                        # Sparkline: last 5 closes oldest to newest
                        sparkline = [float(v) for v in closes.tail(5).tolist()]

                        # Average 5-day volume (daily volumes)
                        if len(volumes) >= 1:
                            avg_5d_volume = int(volumes.mean())

                except Exception as sym_err:
                    logger.warning("Error parsing daily data for %s: %s", bk_sym, sym_err)

            # --- Extract today's volume from intraday ---
            today_volume = avg_5d_volume  # Fallback to daily avg if intraday unavailable

            if intraday_data is not None and not intraday_data.empty:
                try:
                    if is_single or not isinstance(intraday_data.columns, pd.MultiIndex):
                        sym_intraday = intraday_data
                    else:
                        sym_intraday = intraday_data[bk_sym]

                    if not sym_intraday.empty and "Volume" in sym_intraday.columns:
                        vol_series = sym_intraday["Volume"].dropna()
                        today_volume = int(vol_series.sum())
                        # Update last_price from intraday if available
                        if "Close" in sym_intraday.columns:
                            intraday_closes = sym_intraday["Close"].dropna()
                            if not intraday_closes.empty:
                                last_price = float(intraday_closes.iloc[-1])

                except Exception as intra_err:
                    logger.warning("Error parsing intraday data for %s: %s", bk_sym, intra_err)

            # Only store symbols with valid data
            if last_price > 0:
                result[clean_sym] = {
                    "last_price": round(last_price, 4),
                    "change_pct": round(change_pct, 4),
                    "today_volume": today_volume,
                    "avg_5d_volume": avg_5d_volume,
                    "sparkline": sparkline,
                }

        except Exception as e:
            logger.warning("Error processing symbol %s: %s", bk_sym, e)
            continue

    return result


async def fetch_stock_quotes(symbols: list[str]) -> None:
    """
    Async wrapper for _fetch_sync.
    Runs synchronous yfinance calls in a thread pool to avoid blocking the event loop.
    Updates STOCK_DATA global with fresh quote data.
    """
    global STOCK_DATA

    if not symbols:
        logger.warning("fetch_stock_quotes called with empty symbol list")
        return

    logger.info("Fetching quotes for %d symbols", len(symbols))

    try:
        new_data = await asyncio.to_thread(_fetch_sync, symbols)
        STOCK_DATA.update(new_data)
        logger.info(
            "STOCK_DATA updated: %d/%d symbols have valid data",
            len(new_data),
            len(symbols),
        )
    except Exception as e:
        logger.error("fetch_stock_quotes error: %s", e, exc_info=True)


# ---------------------------------------------------------------------------
# Standalone test entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # Test with a few well-known SET stocks
    TEST_SYMBOLS = ["PTT", "AOT", "CPALL", "SCB", "KBANK"]

    async def _main() -> None:
        await fetch_stock_quotes(TEST_SYMBOLS)
        print(f"\nSTOCK_DATA for {len(STOCK_DATA)} symbol(s):")
        for sym, data in STOCK_DATA.items():
            print(
                f"  {sym}: price={data['last_price']:.2f} "
                f"chg={data['change_pct']:+.2f}% "
                f"vol={data['today_volume']:,} "
                f"avg5d={data['avg_5d_volume']:,} "
                f"sparkline={[round(v, 2) for v in data['sparkline']]}"
            )

    asyncio.run(_main())
    sys.exit(0)
