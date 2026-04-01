import MetaTrader5 as mt5
mt5.initialize()
symbols = mt5.symbols_get()
dw_syms = [s for s in symbols if any(x in s.name for x in ['C26','P26','C25','P25','C2604','C2605'])]
for s in dw_syms[:5]:
    mt5.symbol_select(s.name, True)
    info = mt5.symbol_info(s.name)
    if info:
        print(f"{s.name}: contract_size={info.trade_contract_size}, min_lot={info.volume_min}, step={info.volume_step}")
