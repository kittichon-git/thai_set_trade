# signal_logger.py — Persistent signal history for DW Dashboard
# One record per stock per day; each record has a pulse timeline
# Market context: tracks how many stocks are signaling simultaneously
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

import pytz

from models import SignalRecord, SignalPulse, StockSignal

logger = logging.getLogger(__name__)

TZ = pytz.timezone("Asia/Bangkok")

LOG_FILE = Path(__file__).parent / "signal_log.json"
RETENTION_DAYS = 30
PULSE_MIN_SECONDS = 300      # minimum 5 minutes between pulses for same stock
MARKET_WIDE_THRESHOLD = 10   # >= 10 stocks signaling at once = market-wide event

# In-memory store: keyed by "{symbol}_{YYYYMMDD}"
_signal_log: dict[str, SignalRecord] = {}

# Last pulse time per symbol (for pulse dedup)
_last_pulse: dict[str, datetime] = {}


def load_log() -> None:
    """Load signal history from JSON file on startup. Drops records older than RETENTION_DAYS."""
    global _signal_log

    if not LOG_FILE.exists():
        logger.info("No signal log file found at %s, starting fresh.", LOG_FILE)
        _signal_log = {}
        return

    try:
        raw = LOG_FILE.read_text(encoding="utf-8")
        data = json.loads(raw)
        cutoff_date = (datetime.now(TZ) - timedelta(days=RETENTION_DAYS)).strftime("%Y-%m-%d")

        loaded: dict[str, SignalRecord] = {}
        for item in data:
            try:
                record = SignalRecord(**item)
                if record.date >= cutoff_date:
                    loaded[record.id] = record
            except Exception as parse_err:
                logger.warning("Skipping malformed log record: %s", parse_err)

        _signal_log = loaded

        # Rebuild _last_pulse from most recent pulse of each record
        for rec in _signal_log.values():
            if rec.pulses:
                last_time_str = rec.last_seen
                try:
                    dt = TZ.localize(datetime.strptime(f"{rec.date} {last_time_str}", "%Y-%m-%d %H:%M:%S"))
                    _last_pulse[rec.symbol] = dt
                except Exception:
                    pass

        logger.info(
            "Loaded %d signal records (%d stocks, %d symbols in pulse cache)",
            len(_signal_log), len({r.symbol for r in _signal_log.values()}), len(_last_pulse),
        )

    except json.JSONDecodeError as e:
        logger.error("JSON decode error reading signal log: %s", e)
        _signal_log = {}
    except Exception as e:
        logger.error("Failed to load signal log: %s", e, exc_info=True)
        _signal_log = {}


def save_log() -> None:
    """Write current in-memory _signal_log to JSON file."""
    try:
        data = [r.model_dump() for r in _signal_log.values()]
        LOG_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.debug("Signal log saved: %d records", len(_signal_log))
    except Exception as e:
        logger.error("Failed to save signal log: %s", e, exc_info=True)


def record_signals(all_signals: list[StockSignal]) -> None:
    """
    Called after each compute_all_signals() invocation.
    - Groups signals by stock (one record per stock per day)
    - Appends a pulse when signal repeats (min 5 min interval)
    - Records market context: how many stocks are signaling simultaneously
    """
    now = datetime.now(TZ)
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")

    simultaneous = len(all_signals)
    is_market_wide = simultaneous >= MARKET_WIDE_THRESHOLD

    if is_market_wide:
        logger.info(
            "Market-wide event: %d stocks signaling simultaneously", simultaneous
        )

    new_count = 0
    pulse_count = 0

    for sig in all_signals:
        record_id = f"{sig.symbol}_{date_str.replace('-', '')}"
        pulse = SignalPulse(
            time=time_str,
            ratio=round(sig.volume_ratio, 2),
            strength=sig.strength,
        )

        if record_id not in _signal_log:
            # First signal today for this stock
            _signal_log[record_id] = SignalRecord(
                id=record_id,
                date=date_str,
                symbol=sig.symbol,
                first_seen=time_str,
                last_seen=time_str,
                pulses=[pulse],
                max_ratio=round(sig.volume_ratio, 2),
                strength=sig.strength,
                last_price=sig.last_price,
                change_pct=sig.change_pct,
                avg_5d_volume=sig.avg_5d_volume,
                today_volume=sig.today_volume,
                dw_count=len(sig.dw_list),
                dw_codes=[dw.dw_code for dw in sig.dw_list],
                simultaneous_count=simultaneous - 1,  # exclude self
                is_market_wide=is_market_wide,
            )
            _last_pulse[sig.symbol] = now
            new_count += 1
            logger.info(
                "New signal: %s ratio=%.2f strength=%s simultaneous=%d market_wide=%s",
                sig.symbol, sig.volume_ratio, sig.strength, simultaneous, is_market_wide,
            )

        else:
            # Existing record — add pulse if enough time has passed
            last = _last_pulse.get(sig.symbol)
            if last is None or (now - last).total_seconds() >= PULSE_MIN_SECONDS:
                rec = _signal_log[record_id]
                rec.pulses.append(pulse)
                rec.last_seen = time_str
                if sig.volume_ratio > rec.max_ratio:
                    rec.max_ratio = round(sig.volume_ratio, 2)
                    rec.strength = sig.strength
                # Update live snapshot fields
                rec.last_price = sig.last_price
                rec.change_pct = sig.change_pct
                rec.today_volume = sig.today_volume
                _last_pulse[sig.symbol] = now
                pulse_count += 1
                logger.info(
                    "Pulse added: %s ratio=%.2f (pulse #%d)",
                    sig.symbol, sig.volume_ratio, len(rec.pulses),
                )

    if new_count > 0 or pulse_count > 0:
        save_log()
        logger.info(
            "Signal log updated: %d new records, %d pulses added. Total: %d stocks",
            new_count, pulse_count, len(_signal_log),
        )


def get_history(date: str | None = None) -> list[SignalRecord]:
    """
    Return all signal records for the given date (YYYY-MM-DD).
    If date is None, returns today's records (Thai time).
    Sorted by first_seen ascending.
    """
    target = date or datetime.now(TZ).strftime("%Y-%m-%d")
    records = [r for r in _signal_log.values() if r.date == target]
    records.sort(key=lambda r: r.first_seen)
    return records


def get_history_dates() -> list[str]:
    """Return unique dates with signal records, sorted descending."""
    return sorted({r.date for r in _signal_log.values()}, reverse=True)


def get_all_history() -> list[SignalRecord]:
    """Return all records sorted by date+first_seen descending."""
    return sorted(_signal_log.values(), key=lambda r: (r.date, r.first_seen), reverse=True)
