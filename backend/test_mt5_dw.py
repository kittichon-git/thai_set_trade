import MetaTrader5 as mt5

mt5.initialize()

# ลองหา DW code ตัวแรกที่มีใน dw_cache.json
import json
with open("dw_cache.json") as f:
    cache = json.load(f)

# เอา DW code ตัวแรกมาทดสอบ
sample_dw = cache["items"][0]["dwSymbol"] if cache.get("items") else None
print(f"ทดสอบกับ DW: {sample_dw}")

if sample_dw:
    mt5.symbol_select(sample_dw, True)
    tick = mt5.symbol_info_tick(sample_dw)
    info = mt5.symbol_info(sample_dw)
    print(f"info: {info}")
    print(f"tick: {tick}")
