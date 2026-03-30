# signal_engine.py — Advanced Signal Analysis Engine
from __future__ import annotations

import logging
from datetime import datetime, time, timedelta
from typing import Any

import pytz

from models import StockSignal, SignalPulse
from dw_scraper import DW_UNIVERSE
from data_provider import get_provider

logger = logging.getLogger(__name__)
TZ = pytz.timezone("Asia/Bangkok")

# Signal thresholds
OPENING_THRESHOLD    = 2.0   # Current vs Yesterday M15 > 2x
GAP_UP_THRESHOLD     = 0.5   # Gap % threshold
SPIKE_THRESHOLD      = 3.0   # 15m vol > 3x prev 60m avg
MONEY_FLOW_TOP_N     = 50
SIGNIFICANT_JUMP     = 10    # Jump 10+ spots in ranking
SIGNIFICANT_SHARE    = 0.01  # > 1% share of total watchlist value

# State Storage
YESTERDAY_OPENING_VOL: dict[str, int] = {}
INTRADAY_CUM_VOL: dict[str, dict[datetime, int]] = {}
PREV_MONEY_FLOW_RANK: dict[str, int] = {}
HAS_FIRED_TOP_10: set[str] = set()

# SET Market hours (Thai Time)
MORNING_OPEN = time(10, 0)
MONEY_FLOW_SNAPSHOT_TIME = time(10, 10)


async def refresh_m1_history():
    """Startup: Fetch M1 volume for opening comparison and restore intraday cum vol."""
    global YESTERDAY_OPENING_VOL, INTRADAY_CUM_VOL
    provider = get_provider()
    symbols = list(DW_UNIVERSE.keys())
    if not symbols: return
    
    logger.info("Initializing M1 history for %d underlyings...", len(symbols))
    # Fetch last 2 days (up to ~2880 bars)
    history = provider.get_recent_m1_history(symbols, days=2)
    
    now_date = datetime.now(TZ).date()
    
    YESTERDAY_OPENING_VOL.clear()
    INTRADAY_CUM_VOL.clear()
    
    for sym, bars in history.items():
        dates = sorted({dt.date() for dt in bars.keys()})
        # 1. Calculate Yesterday Opening Vol (10:00 - 10:15)
        if len(dates) >= 2:
            yesterday = dates[-2]
            start_time = datetime.combine(yesterday, time(10, 0), tzinfo=TZ)
            end_time = datetime.combine(yesterday, time(10, 15), tzinfo=TZ)
            y_vol = sum(v for dt, v in bars.items() if start_time <= dt <= end_time)
            YESTERDAY_OPENING_VOL[sym] = y_vol
        
        # 2. Rebuild Today's Cumulative Volume for Intraday Spike
        cum_vol = 0
        sym_cum_dict = {}
        for dt, v in sorted(bars.items()):
            if dt.date() == now_date:
                cum_vol += v
                sym_cum_dict[dt.replace(second=0, microsecond=0)] = cum_vol
        if sym_cum_dict:
            INTRADAY_CUM_VOL[sym] = sym_cum_dict

    logger.info("Yesterday's data and Intraday Vol tracker loaded for %d symbols", len(history))


def get_past_cum_vol(sym: str, target_min: datetime) -> int:
    """Helper to find the closest recorded cumulative volume at or before target_min."""
    if sym not in INTRADAY_CUM_VOL:
        return 0
    past_mins = [m for m in INTRADAY_CUM_VOL[sym].keys() if m <= target_min]
    if not past_mins:
        return 0
    return INTRADAY_CUM_VOL[sym][max(past_mins)]


def compute_all_signals() -> list[StockSignal]:
    """
    Core engine loop. Computes the 4 advanced signals:
    1. Opening Vol Anomaly (Today vs Yesterday)
    2. Gap Up + Volume
    3. Intraday Volume Spike (15m vs 60m avg)
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
    curr_min = now.replace(second=0, microsecond=0)
    
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
        today_vol = quote["today_volume"]
        
        # Update Live Intraday Cumulative Volume
        if symbol not in INTRADAY_CUM_VOL:
            INTRADAY_CUM_VOL[symbol] = {}
        # Only update if it grew (prevent reset glitches)
        last_vol = get_past_cum_vol(symbol, curr_min)
        if today_vol >= last_vol:
            INTRADAY_CUM_VOL[symbol][curr_min] = today_vol
        
        sig_type = None
        sig_val = 0.0  # Normalized value for cross-signal sorting
        ratio = 0.0
        
        # 1. Opening Vol Anomaly (First 15 mins)
        # Compare current cumulative vol (up to 15m) vs yesterday's FULL 15m (or proportional)
        if time(10, 0) <= now_time <= time(10, 15):
            y_vol = YESTERDAY_OPENING_VOL.get(symbol, 0)
            if y_vol > 0:
                ratio = today_vol / y_vol
                if ratio >= OPENING_THRESHOLD:
                    sig_type = "Opening Vol"
                    sig_val = ratio
        
        # 2. Gap Up + Vol
        if quote["today_open"] > quote["prev_high"] and quote["prev_high"] > 0:
            if ratio >= OPENING_THRESHOLD:
                sig_type = "Gap Up + Vol"
                gap_pct = ((quote["today_open"] - quote["prev_high"]) / quote["prev_high"]) * 100
                sig_val = gap_pct + ratio # Give boost to Gap Up with high volume

        # 3. Intraday Volume Spike
        if sig_type is None and now_time > time(10, 15):
            vol_15m_ago = get_past_cum_vol(symbol, curr_min - timedelta(minutes=15))
            vol_75m_ago = get_past_cum_vol(symbol, curr_min - timedelta(minutes=75))
            
            vol_last_15 = today_vol - vol_15m_ago
            vol_prev_60 = vol_15m_ago - vol_75m_ago
            
            if vol_prev_60 > 0:
                spike_ratio = vol_last_15 / vol_prev_60
                if spike_ratio >= SPIKE_THRESHOLD:
                    sig_type = "Intraday Spike"
                    sig_val = spike_ratio
                    ratio = spike_ratio
        
        # 4. Money Flow Jumps / Snapshots
        is_mf_signal = False
        if not sig_type:
            # Snapshot at 10:10
            if MONEY_FLOW_SNAPSHOT_TIME <= now_time <= time(10, 11) and rank <= MONEY_FLOW_TOP_N:
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

            if is_mf_signal:
                sig_val = share * 100  # 1.5% -> 1.5

        # Only show signals if price is in the green or neutral (Momentum for Calls/Spikes)
        if sig_type and quote.get("change_pct", 0.0) < 0:
            sig_type = None

        if sig_type:
            strength = "High" if ratio >= 5.0 or share >= 0.05 else "Normal"
            results.append(
                StockSignal(
                    symbol=symbol,
                    last_price=quote["last_price"],
                    change_pct=quote.get("change_pct", 0.0),
                    today_volume=quote["today_volume"],
                    avg_5d_volume=vol_prev_60 if sig_type == "Intraday Spike" else 0, # Used for display
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

    # Sort deeply based on unified signal_value scale
    results.sort(key=lambda x: x.signal_value, reverse=True)
    return results
