# signal_engine.py — Volume anomaly signal computation for DW Dashboard
# Uses pace_ratio (volume rate vs expected at this time) OR total_ratio (>= 2x)
# SET session: 09:30-12:30 + 14:00-16:35 = 335 minutes total
from __future__ import annotations

import logging
from datetime import datetime, time

import pytz

from models import DWItem, StockSignal
from dw_scraper import DW_UNIVERSE
from stock_feed import STOCK_DATA

logger = logging.getLogger(__name__)

TZ = pytz.timezone("Asia/Bangkok")

# SET Thailand session schedule
_MORNING_OPEN  = time(9, 30)
_MORNING_CLOSE = time(12, 30)
_AFTERNOON_OPEN  = time(14, 0)
_AFTERNOON_CLOSE = time(16, 35)
_TOTAL_SESSION_MINUTES = 335  # 180 + 155

# Signal thresholds
PACE_RATIO_THRESHOLD  = 3.0   # volume rate > 3x expected at this time
TOTAL_RATIO_THRESHOLD = 2.0   # or total today >= 2x avg_5d (end-of-day / accumulation)


def _elapsed_session_minutes(now: datetime) -> float:
    """
    Return how many SET session minutes have elapsed today up to `now`.
    Accounts for lunch break (12:30-14:00).
    Returns 0 if market hasn't opened yet.
    """
    t = now.time()

    if t < _MORNING_OPEN:
        return 0.0

    if _MORNING_OPEN <= t <= _MORNING_CLOSE:
        delta = datetime.combine(now.date(), t) - datetime.combine(now.date(), _MORNING_OPEN)
        return delta.total_seconds() / 60.0

    if _MORNING_CLOSE < t < _AFTERNOON_OPEN:
        # Lunch break — count only morning minutes
        return 180.0

    if _AFTERNOON_OPEN <= t <= _AFTERNOON_CLOSE:
        morning = 180.0
        delta = datetime.combine(now.date(), t) - datetime.combine(now.date(), _AFTERNOON_OPEN)
        return morning + delta.total_seconds() / 60.0

    # After close
    return float(_TOTAL_SESSION_MINUTES)


def _compute_pace_ratio(today_vol: int, avg_5d_vol: int, elapsed_min: float) -> float:
    """
    Pace ratio = today_volume / expected_volume_at_this_time
    expected = avg_5d_volume × (elapsed_min / 335)
    """
    if elapsed_min <= 0 or avg_5d_vol <= 0:
        return 0.0
    expected = avg_5d_vol * (elapsed_min / _TOTAL_SESSION_MINUTES)
    return today_vol / max(expected, 1)


def _get_strength(ratio: float) -> str:
    """Categorize signal ratio into strength tier."""
    if ratio >= 5.0:
        return "5x+"
    if ratio >= 3.0:
        return "3x+"
    return "2x+"


def compute_all_signals() -> list[StockSignal]:
    """
    Compute volume anomaly signals for ALL stocks in DW_UNIVERSE.

    Signal fires when EITHER:
      - pace_ratio >= 3.0  (volume arriving faster than 3x normal pace)
      - total_ratio >= 2.0 (total today's volume >= 2x 5-day average)

    Both ratios are computed; the higher is used for ranking/strength.
    Results sorted descending by signal_ratio.
    """
    results: list[StockSignal] = []
    now = datetime.now(TZ)
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    elapsed = _elapsed_session_minutes(now)

    for symbol, dw_list in DW_UNIVERSE.items():
        if symbol not in STOCK_DATA:
            continue

        data = STOCK_DATA[symbol]
        avg_vol   = data.get("avg_5d_volume", 0)
        today_vol = data.get("today_volume", 0)

        if avg_vol == 0:
            continue

        total_ratio = today_vol / avg_vol
        pace_ratio  = _compute_pace_ratio(today_vol, avg_vol, elapsed)

        # Signal fires if either condition met
        if pace_ratio < PACE_RATIO_THRESHOLD and total_ratio < TOTAL_RATIO_THRESHOLD:
            continue

        # Use the higher ratio for ranking and strength label
        signal_ratio = max(pace_ratio, total_ratio)
        strength = _get_strength(signal_ratio)

        results.append(
            StockSignal(
                symbol=symbol,
                last_price=data.get("last_price", 0.0),
                change_pct=data.get("change_pct", 0.0),
                today_volume=today_vol,
                avg_5d_volume=avg_vol,
                volume_ratio=round(signal_ratio, 2),
                strength=strength,
                dw_list=dw_list,
                updated_at=now_str,
                sparkline=data.get("sparkline", []),
            )
        )

    results.sort(key=lambda x: x.volume_ratio, reverse=True)

    if results:
        logger.info(
            "compute_all_signals: %d signals (top: %s %.1fx) elapsed=%.0fmin",
            len(results), results[0].symbol, results[0].volume_ratio, elapsed,
        )
    else:
        logger.debug(
            "compute_all_signals: 0 signals. DW_UNIVERSE=%d STOCK_DATA=%d elapsed=%.0fmin",
            len(DW_UNIVERSE), len(STOCK_DATA), elapsed,
        )

    return results


def compute_signals() -> list[StockSignal]:
    """Return Top 10 signals for dashboard display."""
    return compute_all_signals()[:10]
