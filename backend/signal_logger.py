# signal_logger.py — Signal history and performance tracking via Supabase
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

import pytz

from models import SignalRecord, SignalPulse, StockSignal
from database import supabase
from data_provider import get_provider

logger = logging.getLogger(__name__)
TZ = pytz.timezone("Asia/Bangkok")

# Current Day Cache
_today_signals: dict[str, SignalRecord] = {}
_last_pulse: dict[str, datetime] = {}
PULSE_MIN_SECONDS = 300

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
        
        pulse_obj = SignalPulse(
            time=time_str,
            ratio=sig.volume_ratio,
            strength=sig.strength,
            signal_type=sig.signal_type,
            signal_value=sig.signal_value,
            match_price=entry_price
        )

        if record_id not in _today_signals:
            # Create new Signal Record
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
            _db_upsert_record(rec)
            _db_insert_pulse(record_id, pulse_obj)
            logger.info("New signal saved: %s type=%s entry=%.2f", sig.symbol, sig.signal_type, entry_price)
        else:
            # Check for pulse cooldown
            last_dt = _last_pulse.get(sig.symbol)
            if last_dt is None or (now - last_dt).total_seconds() >= PULSE_MIN_SECONDS:
                rec = _today_signals[record_id]
                rec.pulses.append(pulse_obj)
                rec.last_seen = time_str
                if sig.volume_ratio > rec.max_ratio:
                    rec.max_ratio = sig.volume_ratio
                    rec.strength = sig.strength
                _last_pulse[sig.symbol] = now
                _db_upsert_record(rec)
                _db_insert_pulse(record_id, pulse_obj)
                logger.info("Pulse added: %s type=%s entry=%.2f", sig.symbol, sig.signal_type, entry_price)

def _db_upsert_record(rec: SignalRecord) -> None:
    if supabase is None: return
    data = rec.model_dump()
    data.pop("pulses", None)
    data["record_id"] = data.pop("id")
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
