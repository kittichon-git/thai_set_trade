# signal_logger.py — Persistent signal history for DW Dashboard via Supabase
# One record per stock per day; each record has a pulse timeline stored in DW_signal_pulses
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import pytz

from models import SignalRecord, SignalPulse, StockSignal
from database import supabase

logger = logging.getLogger(__name__)

TZ = pytz.timezone("Asia/Bangkok")

# Signal configuration
RETENTION_DAYS = 30
PULSE_MIN_SECONDS = 300      # minimum 5 minutes between pulses for same stock
MARKET_WIDE_THRESHOLD = 10   # >= 10 stocks signaling at once = market-wide event

# In-memory store for CURRENT DAY ONLY (for performance/UI broadcast)
# Keyed by "{symbol}_{YYYYMMDD}"
_today_signals: dict[str, SignalRecord] = {}

# Last pulse time per symbol (for pulse dedup)
_last_pulse: dict[str, datetime] = {}


def load_log() -> None:
    """
    Initial load of today's signals from Supabase to populate the memory cache.
    Called on startup.
    """
    global _today_signals
    
    if supabase is None:
        logger.warning("Supabase not initialized — skipping load_log")
        return

    now = datetime.now(TZ)
    date_str = now.strftime("%Y-%m-%d")
    
    try:
        # Fetch today's records from DW_signal_records
        # Note: supabase-py handles JOINs/Relations via select syntax
        res = supabase.table("DW_signal_records") \
            .select("*, DW_signal_pulses(*)") \
            .eq("date", date_str) \
            .execute()
        
        loaded: dict[str, SignalRecord] = {}
        for item in res.data:
            # Flatten pulses from sub-query
            pulses_data = item.pop("DW_signal_pulses", [])
            pulses = [SignalPulse(**p) for p in pulses_data]
            pulses.sort(key=lambda x: x.time)
            
            # Map database 'record_id' back to Pydantic 'id'
            if "record_id" in item:
                item["id"] = item.pop("record_id")
            
            record = SignalRecord(**item, pulses=pulses)
            loaded[record.id] = record
            
            if pulses:
                # Update last pulse cache
                last_time_str = record.last_seen
                try:
                    dt = TZ.localize(datetime.strptime(f"{record.date} {last_time_str}", "%Y-%m-%d %H:%M:%S"))
                    _last_pulse[record.symbol] = dt
                except Exception:
                    pass
                    
        _today_signals = loaded
        logger.info("Loaded %d signals for today (%s) from Supabase", len(_today_signals), date_str)
        
    except Exception as e:
        logger.error(f"Failed to load today's log from Supabase: {e}")


def record_signals(all_signals: list[StockSignal]) -> None:
    """
    Called after each compute_all_signals() invocation.
    - Updates in-memory _today_signals
    - Performs upsert to DW_signal_records and insert to DW_signal_pulses in Supabase
    """
    if not all_signals:
        return

    now = datetime.now(TZ)
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")

    simultaneous = len(all_signals)
    is_market_wide = simultaneous >= MARKET_WIDE_THRESHOLD

    if is_market_wide:
        logger.info("Market-wide event: %d stocks signaling simultaneously", simultaneous)

    for sig in all_signals:
        record_id = f"{sig.symbol}_{date_str.replace('-', '')}"
        
        # 1. Check if we should add a pulse
        should_pulse = False
        last = _last_pulse.get(sig.symbol)
        if last is None or (now - last).total_seconds() >= PULSE_MIN_SECONDS:
            should_pulse = True

        pulse_obj = SignalPulse(
            time=time_str,
            ratio=round(sig.volume_ratio, 2),
            strength=sig.strength,
        )

        # 2. Update Memory Cache (_today_signals)
        if record_id not in _today_signals:
            _today_signals[record_id] = SignalRecord(
                id=record_id,
                date=date_str,
                symbol=sig.symbol,
                first_seen=time_str,
                last_seen=time_str,
                pulses=[pulse_obj],
                max_ratio=round(sig.volume_ratio, 2),
                strength=sig.strength,
                last_price=sig.last_price,
                change_pct=sig.change_pct,
                avg_5d_volume=sig.avg_5d_volume,
                today_volume=sig.today_volume,
                dw_count=len(sig.dw_list),
                dw_codes=[dw.dw_code for dw in sig.dw_list],
                simultaneous_count=simultaneous - 1,
                is_market_wide=is_market_wide,
            )
            _last_pulse[sig.symbol] = now
            _db_upsert_record(_today_signals[record_id])
            _db_insert_pulse(record_id, pulse_obj)
            logger.info("New signal saved to DB: %s", sig.symbol)
            
        elif should_pulse:
            rec = _today_signals[record_id]
            rec.pulses.append(pulse_obj)
            rec.last_seen = time_str
            if sig.volume_ratio > rec.max_ratio:
                rec.max_ratio = round(sig.volume_ratio, 2)
                rec.strength = sig.strength
            
            # Fresh stats
            rec.last_price = sig.last_price
            rec.change_pct = sig.change_pct
            rec.today_volume = sig.today_volume
            
            _last_pulse[sig.symbol] = now
            _db_upsert_record(rec)
            _db_insert_pulse(record_id, pulse_obj)
            logger.info("Pulse added to DB: %s (ratio=%.2f)", sig.symbol, sig.volume_ratio)


def _db_upsert_record(rec: SignalRecord) -> None:
    """Helper: Upsert a signal record to Supabase."""
    if supabase is None: return
    try:
        # Convert to dict and remove 'pulses' (it's a separate table)
        data = rec.model_dump()
        data.pop("pulses", None)
        
        # Map pydantic 'id' to database 'record_id'
        data["record_id"] = data.pop("id")
        
        supabase.table("DW_signal_records").upsert(data).execute()
    except Exception as e:
        logger.error(f"Supabase upsert error for {rec.symbol}: {e}")


def _db_insert_pulse(record_id: str, pulse: SignalPulse) -> None:
    """Helper: Insert a pulse to Supabase."""
    if supabase is None: return
    try:
        data = pulse.model_dump()
        data["record_id"] = record_id
        supabase.table("DW_signal_pulses").insert(data).execute()
    except Exception as e:
        logger.error(f"Supabase pulse insert error for {record_id}: {e}")


def get_history(date: str | None = None) -> list[SignalRecord]:
    """
    Return all signal records for the given date (YYYY-MM-DD) from Supabase.
    If date is None, returns today's records.
    """
    target = date or datetime.now(TZ).strftime("%Y-%m-%d")
    
    # If target is today, we can return from memory for speed
    if target == datetime.now(TZ).strftime("%Y-%m-%d") and _today_signals:
        records = list(_today_signals.values())
        records.sort(key=lambda r: r.first_seen)
        return records

    if supabase is None: return []

    try:
        res = supabase.table("DW_signal_records") \
            .select("*, DW_signal_pulses(*)") \
            .eq("date", target) \
            .order("first_seen") \
            .execute()
        
        results: list[SignalRecord] = []
        for item in res.data:
            pulses_data = item.pop("DW_signal_pulses", [])
            pulses = [SignalPulse(**p) for p in pulses_data]
            pulses.sort(key=lambda x: x.time)
            
            if "record_id" in item:
                item["id"] = item.pop("record_id")
            
            results.append(SignalRecord(**item, pulses=pulses))
            
        return results
    except Exception as e:
        logger.error(f"Failed to fetch history from Supabase: {e}")
        return []


def get_history_dates() -> list[str]:
    """Return unique dates with signal records from Supabase."""
    if supabase is None: return []
    try:
        res = supabase.table("DW_signal_records").select("date").execute()
        dates = sorted({item["date"] for item in res.data}, reverse=True)
        return dates
    except Exception as e:
        logger.error(f"Failed to fetch history dates from Supabase: {e}")
        return []


def get_all_history() -> list[SignalRecord]:
    """Return all records from Supabase sorted by date+first_seen descending."""
    if supabase is None: return []
    try:
        res = supabase.table("DW_signal_records") \
            .select("*, DW_signal_pulses(*)") \
            .order("date", desc=True) \
            .order("first_seen", desc=True) \
            .execute()
            
        results: list[SignalRecord] = []
        for item in res.data:
            pulses_data = item.pop("DW_signal_pulses", [])
            pulses = [SignalPulse(**p) for p in pulses_data]
            pulses.sort(key=lambda x: x.time)
            
            if "record_id" in item:
                item["id"] = item.pop("record_id")
            
            results.append(SignalRecord(**item, pulses=pulses))
            
        return results
    except Exception as e:
        logger.error(f"Failed to fetch all history from Supabase: {e}")
        return []
