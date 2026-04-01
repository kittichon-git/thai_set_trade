# models.py — Pydantic v2 data models for DW Dashboard
from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field


class DWItem(BaseModel):
    dw_code: str
    dw_type: str  # "Call" or "Put"
    issuer: str
    dw_price: float
    underlying: str
    gearing: float
    moneyness: str
    expiry_date: str
    days_remaining: int
    dw_volume: int = 0  # today's trading volume from thaiwarrant.com


class StockSignal(BaseModel):
    symbol: str
    last_price: float
    change_pct: float
    today_volume: int
    avg_5d_volume: int
    volume_ratio: float
    strength: str  # "2x+", "3x+", "5x+"
    signal_type: str = "Volume Anomaly"  # "Opening", "Gap Up", "Spike", "Money Flow"
    signal_value: float = 0.0           # Price * Volume (Money Flow)
    dw_list: list[DWItem] = Field(default_factory=list)
    updated_at: str
    sparkline: list[float] = Field(default_factory=list)  # 5 daily closes oldest->newest
    ohlc: list[dict] = Field(default_factory=list)        # [{time, open, high, low, close}]


class DashboardPayload(BaseModel):
    timestamp: str
    market_status: str  # "OPEN", "CLOSED", "PRE-OPEN"
    dw_universe_count: int
    dw_all_count: int = 0
    signal_count: int       # ALL signals (not just top10)
    signals: list[StockSignal] = Field(default_factory=list)  # Top 10 only for display


class WSMessage(BaseModel):
    type: str  # "snapshot" or "ping"
    payload: Optional[DashboardPayload] = None


class SignalPulse(BaseModel):
    time: str       # "10:45:32" — time of this signal occurrence
    ratio: float    # signal ratio at this moment
    strength: str   # "2x+", "3x+", "5x+"
    signal_type: str = "Volume Anomaly"
    signal_value: float = 0.0
    match_price: Optional[float] = None
    day_high_price: Optional[float] = None
    close_price: Optional[float] = None
    profit_high_pct: Optional[float] = None
    profit_close_pct: Optional[float] = None
    # DW ที่ volume สูงสุด ณ ขณะที่สัญญาณยิง
    top_dw_code: Optional[str] = None
    top_dw_volume: Optional[int] = None
    top_dw_bid: Optional[float] = None
    top_dw_ask: Optional[float] = None


class SignalRecord(BaseModel):
    id: str              # "{symbol}_{YYYYMMDD}" — one record per stock per day
    date: str            # "2026-03-29"
    symbol: str
    first_seen: str      # time of first signal
    last_seen: str       # time of most recent signal
    pulses: list[SignalPulse] = Field(default_factory=list)
    max_ratio: float
    strength: str        # based on max_ratio
    # snapshot at first signal
    last_price: float
    change_pct: float
    avg_5d_volume: int
    today_volume: int
    dw_count: int
    dw_codes: list[str] = Field(default_factory=list)
    # market context
    simultaneous_count: int = 0   # other stocks also signaling at first detection
    is_market_wide: bool = False   # True if >= 10 stocks signaling simultaneously
