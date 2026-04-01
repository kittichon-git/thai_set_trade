# main.py — FastAPI application entry point for DW Dashboard
# Provides WebSocket real-time feed + REST API endpoints
from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime

import pytz
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from models import DashboardPayload, WSMessage, StockSignal
from dw_scraper import scrape_dw_universe, scrape_dw_universe_playwright, DW_UNIVERSE, DW_ALL_COLLECTED
from stock_feed import fetch_stock_quotes, STOCK_DATA
from signal_engine import compute_all_signals, refresh_m1_history
from signal_logger import (
    load_log, 
    record_signals, 
    get_history, 
    get_history_dates,
    sync_daily_performance
)
from scheduler import (
    scheduler,
    is_market_open,
    get_market_status,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

TZ = pytz.timezone("Asia/Bangkok")

# Active WebSocket connections
connected_clients: set[WebSocket] = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context — handles startup and shutdown."""
    # --- Startup ---
    logger.info("DW Dashboard starting up...")

    # Load persisted signal history
    load_log()

    # Initialize M1 history for intraday and opening signals
    await refresh_m1_history()

    # Scrape DW universe immediately (Playwright for all issuers, fallback to GET)
    await scrape_dw_universe_playwright()
    if sum(len(v) for v in DW_UNIVERSE.values()) == 0:
        logger.warning("Playwright scrape returned 0 items at startup — falling back to GET")
        await scrape_dw_universe()

    # Start background scheduler (handles daily scrape + feed jobs)
    scheduler.start()
    logger.info("Scheduler started")

    # Launch background tasks
    asyncio.create_task(broadcast_loop(), name="broadcast_loop")
    asyncio.create_task(ping_loop(), name="ping_loop")

    # Fetch initial stock data at startup (always, to populate end-of-day/historical context)
    symbols = list(DW_UNIVERSE.keys())
    if symbols:
        logger.info("Fetching initial stock quotes for %d symbols at startup", len(symbols))
        await fetch_stock_quotes(symbols)
    else:
        logger.info("DW_UNIVERSE is empty — skipping initial stock quote fetch")

    logger.info("DW Dashboard startup complete")
    yield

    # --- Shutdown ---
    logger.info("DW Dashboard shutting down...")
    scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped")


# ---------------------------------------------------------------------------
# CORS configuration
# ---------------------------------------------------------------------------
_cors_origins_env = os.getenv("CORS_ORIGINS", "*")
CORS_ORIGINS = [o.strip() for o in _cors_origins_env.split(",") if o.strip()]

app = FastAPI(
    title="DW Dashboard API",
    version="1.0.0",
    description="Real-time Thai DW Trading Signal Dashboard",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helper: build current dashboard payload
# ---------------------------------------------------------------------------
def build_payload() -> DashboardPayload:
    """
    Compute current signals, record them, and then merge with today's history
    to ensure signals persist even after the market closes or volatility drops.
    """
    # 1. Get currently active (qualifying) signals
    active_sigs = compute_all_signals()
    record_signals(active_sigs)  # Persist them to signal_log.json

    # 2. Get today's historical records from the log
    # This includes everything that fired today, even if not active right now.
    history_records = get_history()

    # 3. Merge: We want one StockSignal per symbol.
    # We'll use the history as the base and update with active signals if present.
    merged_map: dict[str, StockSignal] = {}

    # Initial pass from history
    for rec in history_records:
        # Restore DW list: Call only, top 5 by volume (same as signal_engine)
        all_dws = DW_UNIVERSE.get(rec.symbol, [])
        dw_list = sorted(
            [dw for dw in all_dws if dw.dw_type == 'Call'],
            key=lambda d: d.dw_volume, reverse=True
        )[:5]

        # Get latest pulse for the type and value
        last_pulse = rec.pulses[-1] if rec.pulses else None

        # Pull sparkline + ohlc from live cache
        stock_cache = STOCK_DATA.get(rec.symbol, {})

        merged_map[rec.symbol] = StockSignal(
            symbol=rec.symbol,
            last_price=rec.last_price,
            change_pct=rec.change_pct,
            today_volume=rec.today_volume,
            avg_5d_volume=rec.avg_5d_volume,
            volume_ratio=rec.max_ratio,  # Use max ratio seen today for history
            strength=rec.strength,
            signal_type=last_pulse.signal_type if last_pulse else "Volume Anomaly",
            signal_value=last_pulse.signal_value if last_pulse else 0.0,
            dw_list=dw_list,
            updated_at=f"{rec.date} {rec.last_seen}",
            sparkline=stock_cache.get("sparkline", []),
            ohlc=stock_cache.get("ohlc", []),
        )

    # Overwrite/Update with fresher active signals
    for sig in active_sigs:
        # Active signal is the "truth" for current price/vol
        # We also want to keep the highest ratio seen today
        if sig.symbol in merged_map:
            hist = merged_map[sig.symbol]
            sig.volume_ratio = max(sig.volume_ratio, hist.volume_ratio)
        merged_map[sig.symbol] = sig

    # Convert back to list and sort by volume_ratio descending
    all_merged = list(merged_map.values())
    all_merged.sort(key=lambda s: s.volume_ratio, reverse=True)

    # Send Top 15 to the dashboard (increased to show more of day's activity)
    top_list = all_merged[:15]

    return DashboardPayload(
        timestamp=datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S"),
        market_status=get_market_status(),
        dw_universe_count=sum(len(v) for v in DW_UNIVERSE.values()),
        dw_all_count=sum(len(v) for v in DW_ALL_COLLECTED.values()),
        signal_count=len(all_merged),
        signals=top_list,
    )


# ---------------------------------------------------------------------------
# WebSocket broadcast helpers
# ---------------------------------------------------------------------------
async def broadcast_payload(payload: DashboardPayload) -> None:
    """Send snapshot message to all connected WebSocket clients."""
    if not connected_clients:
        return

    msg = json.dumps({"type": "snapshot", "payload": payload.model_dump()})
    dead: set[WebSocket] = set()

    for ws in connected_clients.copy():
        try:
            await ws.send_text(msg)
        except Exception:
            dead.add(ws)

    if dead:
        connected_clients.difference_update(dead)
        logger.debug("Removed %d dead WebSocket connection(s)", len(dead))


async def broadcast_loop() -> None:
    """
    Continuously build and broadcast payloads to all connected clients.
    - Market OPEN:   broadcast every 10 seconds
    - Market CLOSED: broadcast every 5 minutes (300 seconds)
    """
    while True:
        try:
            interval = 10 if is_market_open() else 300
            payload = build_payload()
            await broadcast_payload(payload)
            await asyncio.sleep(interval)
        except Exception as e:
            logger.error("broadcast_loop error: %s", e, exc_info=True)
            await asyncio.sleep(10)


async def ping_loop() -> None:
    """Send keepalive ping to all clients every 30 seconds."""
    while True:
        await asyncio.sleep(30)
        if not connected_clients:
            continue

        msg = json.dumps({"type": "ping"})
        dead: set[WebSocket] = set()

        for ws in connected_clients.copy():
            try:
                await ws.send_text(msg)
            except Exception:
                dead.add(ws)

        if dead:
            connected_clients.difference_update(dead)


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------
@app.websocket("/ws/dashboard")
async def ws_dashboard(ws: WebSocket) -> None:
    """WebSocket endpoint for real-time dashboard updates."""
    await ws.accept()
    connected_clients.add(ws)
    logger.info("WebSocket client connected. Total clients: %d", len(connected_clients))

    try:
        # Send current snapshot immediately on connect
        payload = build_payload()
        await ws.send_text(json.dumps({"type": "snapshot", "payload": payload.model_dump()}))

        # Keep connection alive (client messages are ignored)
        while True:
            await ws.receive_text()

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug("WebSocket error (likely disconnect): %s", e)
    finally:
        connected_clients.discard(ws)
        logger.info("WebSocket client disconnected. Total clients: %d", len(connected_clients))


# ---------------------------------------------------------------------------
# REST API endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "timestamp": datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S"),
        "dw_universe_count": sum(len(v) for v in DW_UNIVERSE.values()),
        "dw_all_count": sum(len(v) for v in DW_ALL_COLLECTED.values()),
        "dw_underlying_count": len(DW_UNIVERSE),
        "stock_data_count": len(STOCK_DATA),
        "client_count": len(connected_clients),
        "market_status": get_market_status(),
    }


@app.get("/dw-all")
def dw_all_endpoint():
    """Return the FULL DW universe (before filtering) grouped by underlying symbol."""
    return {
        "underlying_count": len(DW_ALL_COLLECTED),
        "total_dw_count": sum(len(v) for v in DW_ALL_COLLECTED.values()),
        "data": {k: [dw.model_dump() for dw in v] for k, v in DW_ALL_COLLECTED.items()},
    }


@app.get("/dw-universe")
def dw_universe_endpoint():
    """Return the full DW universe grouped by underlying symbol."""
    return {
        "underlying_count": len(DW_UNIVERSE),
        "total_dw_count": sum(len(v) for v in DW_UNIVERSE.values()),
        "data": {k: [dw.model_dump() for dw in v] for k, v in DW_UNIVERSE.items()},
    }


@app.get("/signals")
def signals_endpoint():
    """Return all qualifying signals and top 10."""
    all_sigs = compute_all_signals()
    return {
        "count": len(all_sigs),
        "top10": [s.model_dump() for s in all_sigs[:10]],
        "all": [s.model_dump() for s in all_sigs],
    }


@app.get("/scrape-now")
async def scrape_now():
    """Force re-scrape DW universe immediately (Playwright → fallback GET)."""
    from dw_scraper import scrape_dw_universe, scrape_dw_universe_playwright, DW_UNIVERSE
    await scrape_dw_universe_playwright()
    if sum(len(v) for v in DW_UNIVERSE.values()) == 0:
        await scrape_dw_universe()
    return {
        "underlying_count": len(DW_UNIVERSE),
        "total_dw_count": sum(len(v) for v in DW_UNIVERSE.values()),
        "sample": {k: [dw.dw_code for dw in v[:3]] for k, v in list(DW_UNIVERSE.items())[:5]},
    }


@app.get("/dw-debug")
async def dw_debug():
    """Debug: compare GET vs POST response — table structure and all issuer options."""
    import httpx
    from bs4 import BeautifulSoup
    from dw_scraper import HEADERS

    def _table_summary(soup: BeautifulSoup) -> list:
        tables = soup.find_all("table")
        result = []
        for t_idx, t in enumerate(tables[:5]):
            rows = t.find_all("tr")[:4]
            result.append({
                "table_index": t_idx,
                "table_id": t.get("id", ""),
                "table_class": str(t.get("class", "")),
                "rows": [
                    [c.get_text(strip=True) for c in row.find_all(["th", "td"])]
                    for row in rows
                ],
            })
        return result

    def _extract_full_form(soup: BeautifulSoup) -> dict:
        """Extract hidden inputs + select current values for full ASP.NET postback."""
        fields: dict = {}
        for inp in soup.find_all("input", {"type": "hidden"}):
            name = inp.get("name", "")
            if name:
                fields[name] = inp.get("value", "")
        for sel in soup.find_all("select"):
            name = sel.get("name", "")
            if not name:
                continue
            selected = sel.find("option", selected=True)
            if selected:
                fields[name] = selected.get("value", "")
            else:
                first = sel.find("option")
                fields[name] = first.get("value", "") if first else ""
        return fields

    try:
        url = "https://www.thaiwarrant.com/dw/search"
        async with httpx.AsyncClient(headers=HEADERS, timeout=30.0, follow_redirects=True) as client:
            # GET
            r_get = await client.get(url)
            get_soup = BeautifulSoup(r_get.text, "lxml")

            # Extract issuer options
            issuer_sel = get_soup.find("select", {"id": "MainContent_ddIssuer"})
            issuer_options = []
            if issuer_sel:
                for opt in issuer_sel.find_all("option"):
                    issuer_options.append({"value": opt.get("value", ""), "text": opt.get_text(strip=True)})

            # Full form fields for POST
            full_fields = _extract_full_form(get_soup)
            full_fields["__EVENTTARGET"] = "ctl00$MainContent$ddIssuer"
            full_fields["__EVENTARGUMENT"] = ""
            full_fields["ctl00$MainContent$ddIssuer"] = ""  # all issuers

            # POST
            r_post = await client.post(url, data=full_fields)
            post_soup = BeautifulSoup(r_post.text, "lxml")

        return {
            "get_html_bytes": len(r_get.text),
            "get_tables_found": len(get_soup.find_all("table")),
            "get_tables": _table_summary(get_soup),
            "issuer_options": issuer_options,
            "post_form_fields_sent": list(full_fields.keys()),
            "post_status_code": r_post.status_code,
            "post_html_bytes": len(r_post.text),
            "post_raw_preview": r_post.text[:2000],
            "post_tables_found": len(post_soup.find_all("table")),
            "post_tables": _table_summary(post_soup),
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/thaidw-debug")
async def thaidw_debug():
    """Debug: call ScreenerJSONServlet directly and show result."""
    from dw_scraper import _fetch_screener_httpx, _parse_json_items

    try:
        json_items = await _fetch_screener_httpx()
        if not json_items:
            return {
                "raw_count": 0,
                "message": "API returned 0 items — market closed (Mon-Fri 09:30-16:35 BKK)",
            }
        all_items, filtered = _parse_json_items(json_items)
        return {
            "raw_count": len(json_items),
            "parsed_count": len(all_items),
            "filtered_count": len(filtered),
            "issuers": sorted({i.issuer for i in all_items}),
            "sample": [i.model_dump() for i in all_items[:3]],
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/signals/history")
def signals_history(date: str | None = None):
    """
    Return signal history for a given date.
    Query param: date=YYYY-MM-DD (defaults to today Thai time).
    """
    records = get_history(date)
    dates = get_history_dates()
    target_date = date or datetime.now(TZ).strftime("%Y-%m-%d")

    return {
        "date": target_date,
        "count": len(records),
        "records": [r.model_dump() for r in records],
        "available_dates": dates,
    }


# ---------------------------------------------------------------------------
# MT5 Trade endpoint
# ---------------------------------------------------------------------------
class BuyOrderRequest(BaseModel):
    dw_code: str
    volume: float  # MT5 lots


@app.post("/trade/buy")
def trade_buy(req: BuyOrderRequest):
    """Send a market BUY order via MT5. volume = number of lots."""
    from mt5_trader import send_buy_order
    return send_buy_order(req.dw_code, req.volume)
