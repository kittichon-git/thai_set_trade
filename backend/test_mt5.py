import MetaTrader5 as mt5

mt5.initialize()
mt5.symbol_select('AOT', True)

tick = mt5.symbol_info_tick('AOT')
rates = mt5.copy_rates_from_pos('AOT', mt5.TIMEFRAME_D1, 0, 5)

print('tick:', tick)
print('rates:', rates)
