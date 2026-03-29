# dw_scraper.py — Scrape DW universe from thaidw.com ScreenerJSONServlet
# Primary: direct httpx call (fast, no browser)
# Fallback: Playwright (if httpx blocked)
#
# API only returns data during Thai market hours (Mon-Fri ~09:30-16:35 BKK).
# Outside market hours: 0 items → existing data preserved.
#
# DW_UNIVERSE     : filtered (price 0.20-1.20 OR gearing 0.80-1.20, days > 7)
# DW_ALL_COLLECTED: every DW scraped, no filter — /dw-all endpoint
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from datetime import date

import httpx

from models import DWItem

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------
DW_UNIVERSE: dict[str, list[DWItem]] = {}
DW_ALL_COLLECTED: dict[str, list[DWItem]] = {}

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://thaidw.com/tools/dwsearch/",
    "Origin": "https://thaidw.com",
}

_CACHE_FILE = os.path.join(os.path.dirname(__file__), "dw_cache.json")

THAIDW_URL = (
    "https://thaidw.com/tools/dwsearch/"
    "?underlying=all&maturity=all&expiry=all&type=all"
    "&effectiveGearing=all&indicator=all&moneyness=all"
    "&moneynessPercent=all&issuer=all"
)

PRICE_MIN, PRICE_MAX = 0.20, 1.20
GEARING_MIN, GEARING_MAX = 0.80, 1.20
MIN_DAYS = 7

_EN_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
_THAI_MONTHS = {
    "ม.ค.": 1, "ก.พ.": 2, "มี.ค.": 3, "เม.ย.": 4,
    "พ.ค.": 5, "มิ.ย.": 6, "ก.ค.": 7, "ส.ค.": 8,
    "ก.ย.": 9, "ต.ค.": 10, "พ.ย.": 11, "ธ.ค.": 12,
}

# ---------------------------------------------------------------------------
# Parse helpers
# ---------------------------------------------------------------------------
def _parse_float(text: str) -> float:
    try:
        return float(re.sub(r"[^\d.\-]", "", str(text).strip()) or "0")
    except ValueError:
        return 0.0


def _parse_int(text: str) -> int:
    try:
        return int(re.sub(r"[^\d\-]", "", str(text).strip()) or "0")
    except ValueError:
        return 0


def _parse_date(text: str) -> tuple[str, int]:
    """Parse various date formats → (iso_str, days_remaining)."""
    try:
        t = str(text).strip()
        m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{2,4})$", t)
        if m:
            d, mo, y = int(m[1]), int(m[2]), int(m[3])
            if y < 100:
                y += 2000
            expiry = date(y, mo, d)
            return expiry.isoformat(), max((expiry - date.today()).days, 0)
        m = re.match(r"^(\d{1,2})\s+([A-Za-z]{3})\s+(\d{2,4})$", t)
        if m:
            d, mo_str, y = int(m[1]), m[2].lower(), int(m[3])
            mo = _EN_MONTHS.get(mo_str, 0)
            if y < 100:
                y += 2000
            if mo:
                expiry = date(y, mo, d)
                return expiry.isoformat(), max((expiry - date.today()).days, 0)
        parts = t.split()
        if len(parts) == 3:
            mo = _THAI_MONTHS.get(parts[1], 0)
            if mo:
                d, be = int(parts[0]), int(parts[2])
                y = (be + 2500 if be < 100 else be) - 543
                expiry = date(y, mo, d)
                return expiry.isoformat(), max((expiry - date.today()).days, 0)
        m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", t)
        if m:
            expiry = date(int(m[1]), int(m[2]), int(m[3]))
            return expiry.isoformat(), max((expiry - date.today()).days, 0)
    except Exception:
        pass
    return text, 0


def _extract_underlying(dw_code: str) -> str:
    m = re.match(r"^([A-Z]+)", str(dw_code).strip().upper())
    return m.group(1) if m else ""


def _group_and_sort(items: list[DWItem]) -> dict[str, list[DWItem]]:
    universe: dict[str, list[DWItem]] = {}
    for item in items:
        universe.setdefault(item.underlying, []).append(item)
    for sym in universe:
        universe[sym].sort(key=lambda d: d.dw_volume, reverse=True)
    return universe


def _apply_filter(item: DWItem) -> bool:
    return (
        item.days_remaining > MIN_DAYS
        and PRICE_MIN <= item.dw_price <= PRICE_MAX
    )


# ---------------------------------------------------------------------------
# JSON parser — shared by httpx + Playwright paths
# ---------------------------------------------------------------------------
def _parse_json_items(data: list) -> tuple[list[DWItem], list[DWItem]]:
    """Parse ScreenerJSONServlet response items."""
    all_items: list[DWItem] = []
    filtered: list[DWItem] = []
    seen: set[str] = set()

    for raw in data:
        try:
            dw_code = str(raw.get("dwSymbol") or "").strip()
            if not dw_code or dw_code in seen:
                continue
            seen.add(dw_code)

            raw_type = str(raw.get("type") or raw.get("dwType") or raw.get("callPut") or "").upper()
            if "CALL" in raw_type or raw_type == "C":
                dw_type = "Call"
            elif "PUT" in raw_type or raw_type == "P":
                dw_type = "Put"
            else:
                continue

            issuer = str(raw.get("issuer") or "").strip()
            if issuer.lower() == "macquarie":
                issuer = "MACQ"

            underlying = str(raw.get("underlyingSymbol") or "").strip() or _extract_underlying(dw_code)
            if not underlying:
                continue

            dw_price  = _parse_float(str(raw.get("bidPrice_f") or raw.get("bidPrice") or "0").replace(",", ""))
            vol_raw   = str(raw.get("tradeVolume_f") or raw.get("tradeVolume") or "0").replace(",", "")
            dw_volume = int(_parse_float(vol_raw) * 1000)
            gearing   = _parse_float(str(raw.get("effectiveGearing") or "0"))
            moneyness = str(raw.get("moneyness_c") or raw.get("moneyness") or "N/A").strip() or "N/A"
            expiry_iso, days_remaining = _parse_date(str(raw.get("ltDate") or ""))

            item = DWItem(
                dw_code=dw_code, dw_type=dw_type, issuer=issuer,
                dw_price=dw_price, underlying=underlying, gearing=gearing,
                moneyness=moneyness, expiry_date=expiry_iso,
                days_remaining=days_remaining, dw_volume=dw_volume,
            )
            all_items.append(item)
            if _apply_filter(item):
                filtered.append(item)

        except Exception as e:
            logger.debug("JSON item parse error: %s", e)

    return all_items, filtered


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------
def _save_cache(json_items: list) -> None:
    try:
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"saved_at": time.strftime("%Y-%m-%d %H:%M:%S"), "items": json_items}, f)
        logger.info("[cache] Saved %d items to %s", len(json_items), _CACHE_FILE)
    except Exception as e:
        logger.warning("[cache] Save failed: %s", e)


def _load_cache() -> list:
    try:
        if not os.path.exists(_CACHE_FILE):
            return []
        with open(_CACHE_FILE, encoding="utf-8") as f:
            d = json.load(f)
        items = d.get("items", [])
        saved_at = d.get("saved_at", "unknown")
        logger.info("[cache] Loaded %d items (saved %s)", len(items), saved_at)
        return items
    except Exception as e:
        logger.warning("[cache] Load failed: %s", e)
        return []


# ---------------------------------------------------------------------------
# Primary: direct httpx call (fast, no browser overhead)
# ---------------------------------------------------------------------------
async def _fetch_screener_httpx() -> list:
    """
    Call ScreenerJSONServlet directly via httpx.
    Returns raw JSON items list, or [] if empty/error.
    Only returns data during Thai market hours (Mon-Fri ~09:30-16:35 BKK).
    """
    qid = int(time.time() * 1000)
    url = (
        f"https://www.thaidw.com/apimqth/ScreenerJSONServlet"
        f"?underlying=all&type=all&issuer=&maturity=all&moneyness=all"
        f"&moneynessPercent=all&effectiveGearing=all&expiry=all"
        f"&indicator=all&sortBy=&sortOrder=asc&qid={qid}"
    )
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            d = resp.json()
            items = d.get("data") or d.get("dwlist") or []
            logger.info("[httpx] ScreenerJSONServlet → %d items (%d bytes)", len(items), len(resp.content))
            return items
    except Exception as e:
        logger.warning("[httpx] ScreenerJSONServlet failed: %s", e)
        return []


# ---------------------------------------------------------------------------
# Fallback: Playwright (if httpx blocked by WAF)
# ---------------------------------------------------------------------------
def _playwright_fetch_json() -> list:
    """Intercept ScreenerJSONServlet via Playwright (fallback)."""
    from playwright.sync_api import sync_playwright

    result: list = []

    def on_response(res) -> None:
        nonlocal result
        if "ScreenerJSONServlet" in res.url and "init=1" not in res.url:
            try:
                body = res.body()
                if len(body) > 20:
                    d = json.loads(body)
                    items = d.get("data") or d.get("dwlist") or []
                    if items:
                        result = items
                        logger.info("[playwright] Intercepted %d items", len(items))
            except Exception as ex:
                logger.debug("[playwright] Parse error: %s", ex)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        page = browser.new_context(user_agent=HEADERS["User-Agent"]).new_page()
        page.on("response", on_response)
        logger.info("[playwright] Loading thaidw.com...")
        try:
            page.goto(THAIDW_URL, wait_until="domcontentloaded", timeout=60_000)
        except Exception:
            pass
        page.wait_for_timeout(15_000)
        browser.close()

    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
async def scrape_dw_universe_playwright() -> None:
    """
    Scrape DW universe from thaidw.com ScreenerJSONServlet.
    Primary: httpx (fast). Fallback: Playwright.
    Only returns data during Thai market hours (Mon-Fri ~09:30-16:35 BKK).
    Outside market hours: 0 items → existing data preserved.
    """
    global DW_UNIVERSE, DW_ALL_COLLECTED

    # Primary: httpx
    json_items = await _fetch_screener_httpx()

    # Fallback: Playwright (if httpx returned empty)
    if not json_items:
        logger.info("[scraper] httpx empty — trying Playwright fallback...")
        try:
            from playwright.sync_api import sync_playwright  # noqa: F401
            json_items = await asyncio.to_thread(_playwright_fetch_json)
        except ImportError:
            logger.warning("[scraper] Playwright not installed")

    from_cache = False
    if not json_items:
        # Try loading from cache (last successful scrape)
        json_items = _load_cache()
        if json_items:
            from_cache = True
            logger.info("[scraper] Market closed — using cached data (%d items)", len(json_items))
        else:
            logger.warning("[scraper] 0 items and no cache — keeping existing data")
            return

    all_items, filtered = _parse_json_items(json_items)

    if not all_items:
        logger.warning("[scraper] 0 items parsed — existing data preserved")
        return

    # Save to cache only when we got fresh live data (not when loading from cache)
    if not from_cache:
        _save_cache(json_items)

    issuers = sorted({i.issuer for i in all_items})
    logger.info(
        "[scraper] %d total, %d filtered, %d underlyings | issuers: %s",
        len(all_items), len(filtered), len({i.underlying for i in all_items}), issuers,
    )

    DW_ALL_COLLECTED.clear()
    DW_ALL_COLLECTED.update(_group_and_sort(all_items))

    if filtered:
        DW_UNIVERSE.clear()
        DW_UNIVERSE.update(_group_and_sort(filtered))
    else:
        logger.warning("[scraper] 0 filtered items — DW_UNIVERSE unchanged")


async def scrape_dw_universe() -> None:
    """Alias for API compatibility."""
    await scrape_dw_universe_playwright()
