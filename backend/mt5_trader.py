# mt5_trader.py — MT5 market order execution for DW Dashboard
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

try:
    import MetaTrader5 as mt5
    _MT5_AVAILABLE = True
except ImportError:
    mt5 = None  # type: ignore
    _MT5_AVAILABLE = False


def send_buy_order(dw_code: str, volume: float) -> dict:
    """
    Send a market BUY order for a DW symbol via MT5.
    volume = number of MT5 lots (e.g. 1.0, 0.5)
    Returns a dict with success/error info.
    """
    if not _MT5_AVAILABLE:
        return {"success": False, "error": "MetaTrader5 library not installed"}

    if not mt5.initialize():
        err = mt5.last_error()
        return {"success": False, "error": f"MT5 initialize failed: {err}"}

    # Select symbol so MT5 shows market data
    if not mt5.symbol_select(dw_code, True):
        return {"success": False, "error": f"Symbol '{dw_code}' not found or not selectable in MT5"}

    # Get current ask price
    tick = mt5.symbol_info_tick(dw_code)
    if tick is None:
        return {"success": False, "error": f"Cannot get tick data for '{dw_code}' — market may be closed"}

    price = tick.ask
    if price <= 0:
        return {"success": False, "error": f"Ask price is 0 for '{dw_code}' — market may be closed"}

    info = mt5.symbol_info(dw_code)
    filling = mt5.ORDER_FILLING_IOC
    if info and hasattr(info, "filling_mode"):
        if info.filling_mode & mt5.SYMBOL_FILLING_FOK:
            filling = mt5.ORDER_FILLING_FOK
        elif info.filling_mode & mt5.SYMBOL_FILLING_IOC:
            filling = mt5.ORDER_FILLING_IOC

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": dw_code,
        "volume": float(volume),
        "type": mt5.ORDER_TYPE_BUY,
        "price": price,
        "deviation": 20,
        "magic": 234000,
        "comment": "DW Dashboard",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling,
    }

    logger.info("Sending MT5 BUY order: %s vol=%.2f @ %.4f", dw_code, volume, price)
    result = mt5.order_send(request)

    if result is None:
        err = mt5.last_error()
        return {"success": False, "error": f"order_send returned None: {err}"}

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        return {
            "success": False,
            "retcode": result.retcode,
            "error": f"Order rejected (retcode={result.retcode}): {result.comment}",
        }

    logger.info(
        "MT5 BUY order done: symbol=%s order=%d vol=%.2f price=%.4f",
        dw_code, result.order, result.volume, result.price,
    )
    return {
        "success": True,
        "order": result.order,
        "symbol": dw_code,
        "volume": result.volume,
        "price": result.price,
        "comment": result.comment,
    }
