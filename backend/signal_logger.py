# signal_logger.py — Signal history and performance tracking via Supabase
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

import pytz

from models import SignalRecord, SignalPulse, StockSignal
from database import supabase
from data_provider import get_provider

try:
    import MetaTrader5 as _mt5
except ImportError:
    _mt5 = None

def _get_dw_tick(dw_code: str) -> tuple[float, float]:
    """ดึง bid/ask ของ DW จาก MT5 คืนค่า (bid, ask)"""
    if not _mt5:
        return (0.0, 0.0)
    try:
        _mt5.initialize()
        _mt5.symbol_select(dw_code, True)
        tick = _mt5.symbol_info_tick(dw_code)
        if tick:
            return (tick.bid, tick.ask)
    except Exception:
        pass
    return (0.0, 0.0)

logger = logging.getLogger(__name__)
TZ = pytz.timezone("Asia/Bangkok")

# Current Day Cache
_today_signals: dict[str, SignalRecord] = {}
_last_pulse: dict[str, datetime] = {}
_last_money_flow_pulse: dict[str, datetime] = {}  # cooldown แยกสำหรับ Money Flow
PULSE_MIN_SECONDS = 300           # cooldown ทั่วไป 5 นาที
MONEY_FLOW_MIN_SECONDS = 3600     # cooldown Money Flow 1 ชั่วโมง

def load_log() -> None:
    """Startup load of today's signals from Supabase."""
    global _today_signals
    if supabase is None: return
    
    now = datetime.now(TZ)
    date_str = now.strftime("%Y-%m-%d")
    
    try:
        res = supabase.table("DW_signal_records").select("*, DW_signal_pulses(*)").eq("date", date_str).execute()
        loaded = {}
        for item in res.data:
            pulses_raw = item.pop("DW_signal_pulses", [])
            if "record_id" in item: item["id"] = item.pop("record_id")
            pulses = [SignalPulse(**p) for p in pulses_raw]
            record = SignalRecord(**item, pulses=pulses)
            loaded[record.id] = record
            if pulses:
                # Cache last pulse time
                last_time = pulses[-1].time
                dt = TZ.localize(datetime.strptime(f"{record.date} {last_time}", "%Y-%m-%d %H:%M:%S"))
                _last_pulse[record.symbol] = dt
        _today_signals = loaded
        logger.info(f"Loaded {len(_today_signals)} signals for today from Supabase")
    except Exception as e:
        logger.error(f"Failed to load signal log from Supabase: {e}")

def record_signals(all_signals: list[StockSignal]) -> None:
    """Record new signals and pulses with entry price tracking."""
    if not all_signals: return
    
    now = datetime.now(TZ)
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    provider = get_provider()
    
    # We might need bid/ask for entry simulation
    quotes = provider.get_quotes([s.symbol for s in all_signals])

    for sig in all_signals:
        record_id = f"{sig.symbol}_{date_str.replace('-', '')}"
        quote = quotes.get(sig.symbol, {})
        entry_price = quote.get("ask_price") or sig.last_price
        
        # DW ที่ volume สูงสุด ณ ขณะนี้ (dw_list เรียงตาม volume แล้ว)
        top_dw = sig.dw_list[0] if sig.dw_list else None
        top_dw_bid, top_dw_ask = _get_dw_tick(top_dw.dw_code) if top_dw else (0.0, 0.0)

        pulse_obj = SignalPulse(
            time=time_str,
            ratio=sig.volume_ratio,
            strength=sig.strength,
            signal_type=sig.signal_type,
            signal_value=sig.signal_value,
            match_price=entry_price,
            top_dw_code=top_dw.dw_code if top_dw else None,
            top_dw_volume=top_dw.dw_volume if top_dw else None,
            top_dw_bid=top_dw_bid if top_dw_bid > 0 else top_dw.dw_price if top_dw else None,
            top_dw_ask=top_dw_ask if top_dw_ask > 0 else None,
        )

        is_money_flow = sig.signal_type.startswith("Money Flow")

        if record_id not in _today_signals:
            # สำหรับ Money Flow ใหม่ — บันทึก cooldown ด้วย
            rec = SignalRecord(
                id=record_id, date=date_str, symbol=sig.symbol,
                first_seen=time_str, last_seen=time_str,
                pulses=[pulse_obj], max_ratio=sig.volume_ratio,
                strength=sig.strength, last_price=sig.last_price,
                change_pct=sig.change_pct, avg_5d_volume=sig.avg_5d_volume,
                today_volume=sig.today_volume, dw_count=len(sig.dw_list),
                dw_codes=[dw.dw_code for dw in sig.dw_list]
            )
            _today_signals[record_id] = rec
            _last_pulse[sig.symbol] = now
            if is_money_flow:
                _last_money_flow_pulse[sig.symbol] = now
            _db_upsert_record(rec)
            _db_insert_pulse(record_id, pulse_obj)
            logger.info("New signal saved: %s type=%s entry=%.2f", sig.symbol, sig.signal_type, entry_price)
        else:
            # เช็ค cooldown ตามประเภท signal
            if is_money_flow:
                last_dt = _last_money_flow_pulse.get(sig.symbol)
                cooldown = MONEY_FLOW_MIN_SECONDS
            else:
                last_dt = _last_pulse.get(sig.symbol)
                cooldown = PULSE_MIN_SECONDS

            if last_dt is None or (now - last_dt).total_seconds() >= cooldown:
                rec = _today_signals[record_id]
                rec.pulses.append(pulse_obj)
                rec.last_seen = time_str
                if sig.volume_ratio > rec.max_ratio:
                    rec.max_ratio = sig.volume_ratio
                    rec.strength = sig.strength
                _last_pulse[sig.symbol] = now
                if is_money_flow:
                    _last_money_flow_pulse[sig.symbol] = now
                _db_upsert_record(rec)
                _db_insert_pulse(record_id, pulse_obj)
                logger.info("Pulse added: %s type=%s entry=%.2f", sig.symbol, sig.signal_type, entry_price)

def _db_upsert_record(rec: SignalRecord) -> None:
    if supabase is None: return
    data = rec.model_dump()
    data.pop("pulses", None)
    data["record_id"] = data.pop("id")
    # Cap volume values to PostgreSQL integer max (2,147,483,647)
    _MAX_INT = 2_147_483_647
    for key in ("today_volume", "avg_5d_volume"):
        if data.get(key) is not None:
            data[key] = min(int(data[key]), _MAX_INT)
    try:
        supabase.table("DW_signal_records").upsert(data).execute()
    except Exception as e:
        logger.error(f"Supabase record upsert error: {e}")

def _db_insert_pulse(record_id: str, pulse: SignalPulse) -> None:
    if supabase is None: return
    data = pulse.model_dump()
    data["record_id"] = record_id
    try:
        supabase.table("DW_signal_pulses").insert(data).execute()
    except Exception as e:
        logger.error(f"Supabase pulse insert error: {e}")

def get_history(date: str | None = None) -> list[SignalRecord]:
    """Return signal records for a given date (default: today). Queries Supabase for past dates."""
    import pytz as _pytz
    tz = _pytz.timezone("Asia/Bangkok")
    target = date or datetime.now(tz).strftime("%Y-%m-%d")
    today = datetime.now(tz).strftime("%Y-%m-%d")

    # Today's records are in memory
    if target == today:
        return list(_today_signals.values())

    # Past dates: query Supabase
    if supabase is None:
        return []
    try:
        res = supabase.table("DW_signal_records").select("*, DW_signal_pulses(*)").eq("date", target).execute()
        records = []
        for item in res.data:
            pulses_raw = item.pop("DW_signal_pulses", [])
            if "record_id" in item:
                item["id"] = item.pop("record_id")
            pulses = [SignalPulse(**p) for p in pulses_raw]
            records.append(SignalRecord(**item, pulses=pulses))
        return records
    except Exception as e:
        logger.error(f"get_history error for {target}: {e}")
        return []


def get_history_dates() -> list[str]:
    """Return list of dates that have signal records in Supabase."""
    if supabase is None:
        return []
    try:
        res = supabase.table("DW_signal_records").select("date").execute()
        dates = sorted({item["date"] for item in res.data}, reverse=True)
        return dates
    except Exception as e:
        logger.error(f"get_history_dates error: {e}")
        return []


async def sync_daily_performance():
    """Execute at EOD (16:40) to update day_high and close_price and calculate P/L."""
    if supabase is None: return
    
    now = datetime.now(TZ)
    date_str = now.strftime("%Y-%m-%d")
    logger.info("Syncing daily performance for %s...", date_str)
    
    provider = get_provider()
    
    # 1. Fetch all pulses for today
    res = supabase.table("DW_signal_pulses") \
        .select("*, DW_signal_records(symbol)") \
        .filter("created_at", "gte", date_str) \
        .execute()
    
    if not res.data:
        logger.info("No pulses to update for today.")
        return
        
    # Get unique symbols
    symbols = list({item["DW_signal_records"]["symbol"] for item in res.data})
    quotes = provider.get_quotes(symbols)
    
    # 2. Update each pulse with High/Close/Profit
    for item in res.data:
        symbol = item["DW_signal_records"]["symbol"]
        q = quotes.get(symbol)
        if not q: continue
        
        match_price = item["match_price"]
        day_high = q.get("today_high") or q.get("last_price")
        close_price = q.get("last_price")
        
        if match_price and match_price > 0:
            profit_high = round((day_high - match_price) / match_price * 100, 2)
            profit_close = round((close_price - match_price) / match_price * 100, 2)
        else:
            profit_high = profit_close = 0.0
            
        try:
            supabase.table("DW_signal_pulses").update({
                "day_high_price": day_high,
                "close_price": close_price,
                "profit_high_pct": profit_high,
                "profit_close_pct": profit_close
            }).eq("id", item["id"]).execute()
        except Exception as e:
            logger.error(f"Failed to update pulse profit for {symbol}: {e}")

    logger.info("Daily performance sync complete.")
