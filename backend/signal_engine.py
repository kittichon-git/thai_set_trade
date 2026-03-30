# signal_engine.py — Advanced Signal Analysis Engine
from __future__ import annotations

import logging
from datetime import datetime, time, timedelta
from typing import Any, Optional

import pytz

from models import StockSignal, SignalPulse
from dw_scraper import DW_UNIVERSE
from data_provider import get_provider

logger = logging.getLogger(__name__)
TZ = pytz.timezone("Asia/Bangkok")

# Signal thresholds
OPENING_THRESHOLD    = 2.0   # Current M1 vs Yesterday M1 > 2x
GAP_UP_THRESHOLD     = 0.5   # Open > PrevHigh + 0.5% buffer? (Open > PrevHigh)
SPIKE_THRESHOLD      = 3.0   # 10m vol > 3x prev 60m avg
MONEY_FLOW_TOP_N     = 50
SIGNIFICANT_JUMP     = 10    # Jump 10+ spots in ranking
SIGNIFICANT_SHARE    = 0.01  # > 1% share of total watchlist value

# State Storage
YESTERDAY_M1_DATA: dict[str, list[int]] = {}  # {symbol: [vol1, vol2, ..., vol15]}
# Rolling volume for spike detection: {symbol: [vol_m1, vol_m2, ..., vol_m60]}
ROLLING_VOL_HISTORY: dict[str, list[int]] = {} 
# Previous Money Flow Ranking to detect jumps: {symbol: rank}
PREV_MONEY_FLOW_RANK: dict[str, int] = {}
# Stocks that have already fired a "Top 10" pulse today
HAS_FIRED_TOP_10: set[str] = set()

# SET Market hours (Thai Time)
MORNING_OPEN = time(10, 0)
MONEY_FLOW_SNAPSHOT_TIME = time(10, 10)


async def initialize_yesterday_data():
    """Startup: Fetch yesterday's M1 volume for opening comparison."""
    global YESTERDAY_M1_DATA
    provider = get_provider()
    symbols = list(DW_UNIVERSE.keys())
    if not symbols: return
    
    logger.info("Initializing yesterday's M1 data for %d underlyings...", len(symbols))
    data = provider.get_yesterday_morning_data(symbols)
    YESTERDAY_M1_DATA.update(data)
    logger.info("Yesterday's data loaded for %d symbols", len(YESTERDAY_M1_DATA))


def compute_all_signals() -> list[StockSignal]:
    """
    Core engine loop. Computes the 4 advanced signals:
    1. Opening Vol Anomaly (Today vs Yesterday)
    2. Gap Up + Volume
    3. Intraday Volume Spike (10m vs 60m avg)
    4. Market Money Flow Share (Top 50)
    """
    provider = get_provider()
    symbols = list(DW_UNIVERSE.keys())
    if not symbols: return []
    
    quotes = provider.get_quotes(symbols)
    if not quotes: return []
    
    results: list[StockSignal] = []
    now = datetime.now(TZ)
    now_time = now.time()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    # -----------------------------------------------------------------------
    # Logic 4: Money Flow Calculation (Total Watchlist Value)
    # -----------------------------------------------------------------------
    stock_values = []
    for s, q in quotes.items():
        val = q["last_price"] * q["today_volume"]
        stock_values.append({"symbol": s, "value": val, "quote": q})
    
    total_market_value = sum(item["value"] for item in stock_values)
    # Sort by value descending
    stock_values.sort(key=lambda x: x["value"], reverse=True)
    
    for i, item in enumerate(stock_values):
        item["rank"] = i + 1
        item["share"] = item["value"] / max(total_market_value, 1)

    # -----------------------------------------------------------------------
    # Signal Analysis per Stock
    # -----------------------------------------------------------------------
    for rank, item in enumerate(stock_values[:100]): # Process top 100 for signals
        symbol = item["symbol"]
        quote = item["quote"]
        share = item["share"]
        rank = item["rank"]
        
        sig_type = None
        sig_val = item["value"]
        ratio = 0.0
        
        # 1. Opening Vol Anomaly (First 15 mins)
        if time(10, 0) <= now_time <= time(10, 15):
            y_vols = YESTERDAY_M1_DATA.get(symbol, [])
            if y_vols:
                # Comparison logic (simplified: compare cumulative today vs yesterday)
                today_vol = quote["today_volume"]
                y_cum_vol = sum(y_vols[:now.minute]) # index by elapsed mins
                if y_cum_vol > 0:
                    ratio = today_vol / y_cum_vol
                    if ratio >= OPENING_THRESHOLD:
                        sig_type = "Opening Vol"
        
        # 2. Gap Up + Vol
        if sig_type is None and quote["today_open"] > quote["prev_high"] and quote["prev_high"] > 0:
            # We already have a volume anomaly if ratio was high
            if ratio >= OPENING_THRESHOLD:
                sig_type = "Gap Up + Vol"

        # 3. Intraday Volume Spike
        # Requires background Rolling Volume updates (not implemented here for brevity)
        # But if today_volume jumps 3x compared to our last known cumulative...
        
        # 4. Money Flow Jumps / Snapshots
        is_mf_signal = False
        if not sig_type:
            # Snapshot at 10:10
            if MONEY_FLOW_SNAPSHOT_TIME <= now_time <= time(10, 11):
                if rank <= MONEY_FLOW_TOP_N:
                    sig_type = "Money Flow (Snapshot)"
                    is_mf_signal = True
            
            # Significant Jump
            prev_rank = PREV_MONEY_FLOW_RANK.get(symbol)
            if not is_mf_signal and prev_rank and prev_rank - rank >= SIGNIFICANT_JUMP:
                sig_type = "Money Flow (Jump)"
                is_mf_signal = True
            
            # Entering Top 10 first time
            if not is_mf_signal and rank <= 10 and symbol not in HAS_FIRED_TOP_10:
                sig_type = "Money Flow (Top 10)"
                HAS_FIRED_TOP_10.add(symbol)
                is_mf_signal = True
                
            # Significant Share
            if not is_mf_signal and share >= SIGNIFICANT_SHARE:
                sig_type = "Money Flow (High Share)"
                is_mf_signal = True

        # Only show signals if price is in the green (Momentum for Calls)
        if sig_type and quote.get("change_pct", 0.0) <= 0:
            sig_type = None

        if sig_type:
            strength = "High" if ratio >= 5.0 or share >= 0.05 else "Normal"
            results.append(
                StockSignal(
                    symbol=symbol,
                    last_price=quote["last_price"],
                    change_pct=quote.get("change_pct", 0.0),
                    today_volume=quote["today_volume"],
                    avg_5d_volume=0, # MT5 doesn't provide this easily
                    volume_ratio=round(ratio, 2),
                    strength=strength,
                    signal_type=sig_type,
                    signal_value=sig_val,
                    dw_list=DW_UNIVERSE.get(symbol, []),
                    updated_at=now_str,
                    sparkline=quote.get("sparkline", [])
                )
            )
        
        # Update previous rank for next iteration
        PREV_MONEY_FLOW_RANK[symbol] = rank

    results.sort(key=lambda x: x.signal_value, reverse=True)
    return results
