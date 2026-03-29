# scheduler.py — APScheduler jobs + Thai holiday calendar for DW Dashboard
# Manages daily DW scrape and periodic stock quote refresh
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, time

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from dw_scraper import scrape_dw_universe, scrape_dw_universe_playwright, DW_UNIVERSE
from stock_feed import fetch_stock_quotes

logger = logging.getLogger(__name__)

TZ = pytz.timezone("Asia/Bangkok")

# Thai public holidays 2026 (SET exchange closure dates)
THAI_HOLIDAYS_2026: set[str] = {
    "2026-01-01",  # New Year's Day
    "2026-02-05",  # Makha Bucha Day
    "2026-04-06",  # Chakri Memorial Day
    "2026-04-13",  # Songkran Festival
    "2026-04-14",  # Songkran Festival
    "2026-04-15",  # Songkran Festival
    "2026-05-01",  # National Labour Day
    "2026-05-04",  # Coronation Day
    "2026-05-11",  # Visakha Bucha Day (estimated)
    "2026-06-03",  # HM Queen's Birthday
    "2026-07-06",  # Asanha Bucha Day (estimated)
    "2026-07-28",  # HM King's Birthday
    "2026-08-12",  # HM Queen Mother's Birthday
    "2026-10-13",  # Passing of King Rama IX Memorial Day
    "2026-10-23",  # Chulalongkorn Day
    "2026-12-05",  # HM Late King Rama IX Birthday
    "2026-12-10",  # Constitution Day
    "2026-12-31",  # New Year's Eve
}


def is_trading_day() -> bool:
    """Return True if today is a regular SET trading day (weekday, not holiday)."""
    now = datetime.now(TZ)
    if now.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    date_str = now.strftime("%Y-%m-%d")
    return date_str not in THAI_HOLIDAYS_2026


def is_market_open() -> bool:
    """
    Return True if SET market is currently open.
    Trading hours: 09:30 - 16:35 Thai time, Mon-Fri, excluding holidays.
    """
    now = datetime.now(TZ)
    if not is_trading_day():
        return False
    t = now.time()
    return time(9, 30) <= t <= time(16, 35)


def get_market_status() -> str:
    """
    Return current market status string.
    - "OPEN"      — 09:30-16:35 on trading days
    - "PRE-OPEN"  — 09:00-09:29 on trading days
    - "CLOSED"    — all other times, weekends, holidays
    """
    now = datetime.now(TZ)
    if not is_trading_day():
        return "CLOSED"
    t = now.time()
    if time(9, 0) <= t < time(9, 30):
        return "PRE-OPEN"
    if time(9, 30) <= t <= time(16, 35):
        return "OPEN"
    return "CLOSED"


async def daily_scrape_job() -> None:
    """
    Scheduler job: scrape DW universe from thaiwarrant.com (all issuers via Playwright).
    Falls back to GET-only scraper if Playwright fails.
    Runs once daily at 08:50 on weekdays.
    Also called immediately at startup via lifespan.
    """
    logger.info("daily_scrape_job: starting DW universe scrape (Playwright — all issuers)")
    try:
        await scrape_dw_universe_playwright()
        total = sum(len(v) for v in DW_UNIVERSE.values())
        if total == 0:
            logger.warning("Playwright returned 0 items — falling back to GET scraper")
            await scrape_dw_universe()
            total = sum(len(v) for v in DW_UNIVERSE.values())
        logger.info("daily_scrape_job: complete — %d underlying symbols, %d total DW items", len(DW_UNIVERSE), total)
    except Exception as e:
        logger.error("daily_scrape_job error: %s — falling back to GET scraper", e, exc_info=True)
        await scrape_dw_universe()


async def stock_feed_job() -> None:
    """
    Scheduler job: fetch latest stock quotes for all DW underlying symbols.
    Only executes if the market is currently open.
    Triggered every 10 seconds via interval job (during market hours).
    """
    if not is_market_open():
        logger.debug("stock_feed_job: market closed, skipping")
        return

    symbols = list(DW_UNIVERSE.keys())
    if not symbols:
        logger.debug("stock_feed_job: DW_UNIVERSE is empty, skipping")
        return

    logger.debug("stock_feed_job: fetching quotes for %d symbols", len(symbols))
    try:
        await fetch_stock_quotes(symbols)
    except Exception as e:
        logger.error("stock_feed_job error: %s", e, exc_info=True)


# APScheduler instance (AsyncIOScheduler — integrates with FastAPI's event loop)
scheduler = AsyncIOScheduler(timezone=TZ)

# Job 1: Daily DW universe scrape at 08:50 Mon-Fri
scheduler.add_job(
    daily_scrape_job,
    trigger="cron",
    day_of_week="mon-fri",
    hour=8,
    minute=50,
    id="daily_scrape",
    name="Daily DW Universe Scrape",
    replace_existing=True,
    misfire_grace_time=300,
)

# Job 2: Stock feed refresh every 10 seconds (checks is_market_open internally)
scheduler.add_job(
    stock_feed_job,
    trigger="interval",
    seconds=10,
    id="stock_feed",
    name="Stock Feed Refresh",
    replace_existing=True,
    misfire_grace_time=10,
)

# Job 3: DW universe refresh every 10 minutes during market hours
async def intraday_scrape_job() -> None:
    if not is_market_open():
        return
    logger.info("intraday_scrape_job: refreshing DW universe")
    await scrape_dw_universe_playwright()

scheduler.add_job(
    intraday_scrape_job,
    trigger="interval",
    minutes=10,
    id="intraday_scrape",
    name="Intraday DW Universe Refresh",
    replace_existing=True,
    misfire_grace_time=60,
)
