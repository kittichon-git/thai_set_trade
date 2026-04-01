import MetaTrader5 as mt5

mt5.initialize()
mt5.symbol_select('AOT', True)

tick = mt5.symbol_info_tick('AOT')
book = mt5.market_book_get('AOT')

print(f"Bid: {tick.bid}")
print(f"Ask: {tick.ask}")
print(f"Last: {tick.last}")
print(f"\nOrder Book (market_book_get):")
if book:
    for entry in book[:10]:
        print(f"  type={entry.type} price={entry.price} volume={entry.volume}")
else:
    print("  ไม่มีข้อมูล Order Book")
