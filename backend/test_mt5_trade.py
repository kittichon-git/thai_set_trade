import MetaTrader5 as mt5

mt5.initialize()

# ดูข้อมูล account
info = mt5.account_info()
print(f"Login: {info.login}")
print(f"Server: {info.server}")
print(f"Balance: {info.balance}")
print(f"Trade allowed: {info.trade_allowed}")
print(f"Trade expert: {info.trade_expert}")  # ต้องเป็น True ถึงจะส่ง order ได้
