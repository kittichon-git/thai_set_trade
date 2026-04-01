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
MONEY_FLOW_TOP_N     = 5     # Top 5 by money flow share

# Late Surge thresholds (M1-based, dynamic by time of day)
LATE_SURGE_AVG_LOOKBACK  = 30   # ใช้ M1 ย้อนหลัง 30 นาทีคำนวณ avg
LATE_SURGE_MIN_PERIODS   = 10   # ต้องมี M1 data อย่างน้อย 10 นาที
LATE_SURGE_MIN_M1_VOL    = 2000 # volume ขั้นต่ำต่อ M1 (กรอง noise tick)
LATE_SURGE_PREV_CONFIRM  = 0.3  # vol_m1_prev ต้องอย่างน้อย 30% ของ MIN_M1_VOL

def _late_surge_threshold(t: time) -> float:
    """Threshold ลดลงช่วงบ่าย เพราะ volume เบากว่าเช้า."""
    if t < time(11, 30):
        return 4.0   # เช้า — volume ปกติสูง ต้องเกณฑ์สูง
    elif t < time(14, 30):
        return 3.0   # กลางวัน
    else:
        return 2.5   # บ่าย — burst เล็กก็มีนัย

# State Storage
YESTERDAY_OPENING_CUM: dict[str, dict[int, int]] = {}  # sym -> {minute_offset: cum_vol}
INTRADAY_CUM_VOL: dict[str, dict[datetime, int]] = {}
GAP_UP_FIRED_TODAY: set[str] = set()       # symbols ที่ Gap Up ยิงไปแล้ววันนี้
OPENING_VOL_FIRED_TODAY: set[str] = set()  # symbols ที่ Opening Vol ยิงไปแล้ววันนี้
_GAP_UP_DATE: str = ""                     # วันที่ reset ล่าสุด

# SET Market hours (Thai Time)
MORNING_OPEN = time(10, 0)


async def refresh_m1_history():
    """Startup: Fetch M1 volume for opening comparison and restore intraday cum vol."""
    global YESTERDAY_OPENING_CUM, INTRADAY_CUM_VOL
    provider = get_provider()
    symbols = list(DW_UNIVERSE.keys())
    if not symbols: return

    logger.info("Initializing M1 history for %d underlyings...", len(symbols))
    history = provider.get_recent_m1_history(symbols, days=2)

    now_date = datetime.now(TZ).date()

    YESTERDAY_OPENING_CUM.clear()
    INTRADAY_CUM_VOL.clear()

    for sym, bars in history.items():
        dates = sorted({dt.date() for dt in bars.keys()})

        # 1. Yesterday per-minute cumulative vol ช่วง 10:00-10:15
        if len(dates) >= 2:
            yesterday = dates[-2]
            cum = 0
            per_min: dict[int, int] = {}
            for dt, v in sorted(bars.items()):
                if dt.date() == yesterday and time(10, 0) <= dt.time() <= time(10, 15):
                    offset = (dt.hour - 10) * 60 + dt.minute  # 0=10:00, 1=10:01, ...
                    cum += v
                    per_min[offset] = cum
            if per_min:
                YESTERDAY_OPENING_CUM[sym] = per_min

        # 2. Rebuild Today's Cumulative Volume for Intraday Spike
        cum_vol = 0
        sym_cum_dict = {}
        for dt, v in sorted(bars.items()):
            if dt.date() == now_date:
                cum_vol += v
                sym_cum_dict[dt.replace(second=0, microsecond=0)] = cum_vol
        if sym_cum_dict:
            INTRADAY_CUM_VOL[sym] = sym_cum_dict

    logger.info("Yesterday opening cum-vol and intraday tracker loaded for %d symbols", len(history))


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
    Core engine loop. Computes the 5 advanced signals:
    1. Opening Vol Anomaly (Today vs Yesterday)
    2. Gap Up + Volume
    3. Late Surge (M5 burst vs rolling avg — all day)
    4. Intraday Volume Spike (15m vs 60m avg)
    5. Market Money Flow Share (Top 50)
    """
    provider = get_provider()
    symbols = list(DW_UNIVERSE.keys())
    if not symbols: return []
    
    quotes = provider.get_quotes(symbols)
    if not quotes: return []
    
    global GAP_UP_FIRED_TODAY, _GAP_UP_DATE

    results: list[StockSignal] = []
    now = datetime.now(TZ)
    now_time = now.time()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    curr_min = now.replace(second=0, microsecond=0)

    # Reset trackers ทุกวันใหม่
    today_str = now.strftime("%Y-%m-%d")
    if today_str != _GAP_UP_DATE:
        GAP_UP_FIRED_TODAY.clear()
        OPENING_VOL_FIRED_TODAY.clear()
        _GAP_UP_DATE = today_str
    
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
        avg5d = quote.get("avg_5d_volume", 0)

        # 1. Opening Vol Anomaly (10:00-10:15) — เปรียบเทียบนาทีต่อนาทีกับเมื่อวาน
        if time(10, 0) <= now_time <= time(10, 15) and symbol not in OPENING_VOL_FIRED_TODAY:
            minute_offset = (now.hour - 10) * 60 + now.minute
            y_cum_at_m = YESTERDAY_OPENING_CUM.get(symbol, {}).get(minute_offset, 0)
            if y_cum_at_m > 0:
                today_cum_at_m = get_past_cum_vol(symbol, curr_min)
                ratio = today_cum_at_m / y_cum_at_m
                if ratio >= OPENING_THRESHOLD:
                    sig_type = "Opening Vol"
                    sig_val = ratio
                    OPENING_VOL_FIRED_TODAY.add(symbol)
        
        # 2. Gap Up + Vol (ยิงได้แค่ครั้งเดียวต่อวันต่อ symbol)
        if symbol not in GAP_UP_FIRED_TODAY and quote.get("today_open", 0) > quote.get("prev_high", 0) > 0:
            avg5d = quote.get("avg_5d_volume", 0)
            gap_ratio = (today_vol / avg5d) if avg5d > 0 else 0.0
            if gap_ratio >= OPENING_THRESHOLD:
                sig_type = "Gap Up + Vol"
                gap_pct = ((quote["today_open"] - quote["prev_high"]) / quote["prev_high"]) * 100
                ratio = gap_ratio
                sig_val = gap_pct + gap_ratio
                GAP_UP_FIRED_TODAY.add(symbol)

        # 3. Late Surge — M1 volume burst เทียบกับ avg M1 ย้อนหลัง 30 นาที
        if sig_type is None and now_time >= time(10, 30):
            # Volume นาทีปัจจุบัน
            vol_m1_now  = today_vol - get_past_cum_vol(symbol, curr_min - timedelta(minutes=1))
            # Volume นาทีก่อนหน้า (ใช้ยืนยันความต่อเนื่อง)
            vol_m1_prev = (get_past_cum_vol(symbol, curr_min - timedelta(minutes=1))
                           - get_past_cum_vol(symbol, curr_min - timedelta(minutes=2)))

            # คำนวณ avg M1 จาก LATE_SURGE_AVG_LOOKBACK นาทีย้อนหลัง
            m1_vols: list[int] = []
            for n in range(2, LATE_SURGE_AVG_LOOKBACK + 2):   # เริ่มจาก -2 min เพื่อไม่นับนาทีปัจจุบัน
                v_end   = get_past_cum_vol(symbol, curr_min - timedelta(minutes=n))
                v_start = get_past_cum_vol(symbol, curr_min - timedelta(minutes=n + 1))
                pv = v_end - v_start
                if pv >= 0:
                    m1_vols.append(pv)

            min_prev_vol = int(LATE_SURGE_MIN_M1_VOL * LATE_SURGE_PREV_CONFIRM)

            if (len(m1_vols) >= LATE_SURGE_MIN_PERIODS
                    and vol_m1_now  >= LATE_SURGE_MIN_M1_VOL
                    and vol_m1_prev >= min_prev_vol):
                avg_m1 = sum(m1_vols) / len(m1_vols)
                if avg_m1 > 0:
                    surge_ratio = vol_m1_now / avg_m1
                    if surge_ratio >= _late_surge_threshold(now_time):
                        sig_type = "Late Surge"
                        sig_val  = surge_ratio
                        ratio    = surge_ratio

        # 4. Intraday Volume Spike
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
        
        # 5. Money Flow Top 5 (runs all day — top 5 by share of total watchlist value)
        if not sig_type and rank <= MONEY_FLOW_TOP_N:
            sig_type = f"Money Flow #{rank}"
            sig_val = share * 100   # e.g. 2.5 for 2.5%
            ratio = share * 100     # reuse ratio field for badge display

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
                    avg_5d_volume=vol_prev_60 if sig_type == "Intraday Spike" else avg5d,
                    volume_ratio=round(ratio, 2),
                    strength=strength,
                    signal_type=sig_type,
                    signal_value=sig_val,
                    dw_list=sorted(
                        [dw for dw in DW_UNIVERSE.get(symbol, []) if dw.dw_type == 'Call'],
                        key=lambda d: d.dw_volume, reverse=True
                    )[:5],
                    updated_at=now_str,
                    sparkline=quote.get("sparkline", []),
                    ohlc=quote.get("ohlc", [])
                )
            )
        
    # Sort deeply based on unified signal_value scale
    results.sort(key=lambda x: x.signal_value, reverse=True)
    return results
