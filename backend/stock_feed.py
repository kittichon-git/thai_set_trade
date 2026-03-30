# stock_feed.py — Hybrid data feed wrapper for DW Dashboard
from __future__ import annotations

import asyncio
import logging
from typing import Any

from data_provider import get_provider

logger = logging.getLogger(__name__)

# Global cache — updated every 10s during market hours
# Structure per symbol: {last_price, change_pct, today_volume, avg_5d_volume, sparkline}
STOCK_DATA: dict[str, dict[str, Any]] = {}

async def fetch_stock_quotes(symbols: list[str]) -> None:
    """
    Sync wrapper to update STOCK_DATA from the active provider.
    This replaces the old redundant yfinance fetching logic.
    """
    global STOCK_DATA

    if not symbols:
        return

    logger.debug("Fetching quotes for %d symbols via provider", len(symbols))

    try:
        # get_quotes(symbols) internally handles MT5 vs Yahoo and caching
        new_data = get_provider().get_quotes(symbols, force_refresh=True)
        STOCK_DATA.update(new_data)
        logger.debug("STOCK_DATA updated from provider (%d symbols)", len(new_data))
    except Exception as e:
        logger.error("fetch_stock_quotes (provider) error: %s", e)

# Entry point for standalone testing (now simpler)
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    TEST_SYMBOLS = ["PTT", "AOT", "CPALL"]

    async def _main() -> None:
        await fetch_stock_quotes(TEST_SYMBOLS)
        for sym, d in STOCK_DATA.items():
            print(f"  {sym}: {d.get('last_price')} {d.get('change_pct'):+.2f}% vol={d.get('today_volume')}")

    asyncio.run(_main())
