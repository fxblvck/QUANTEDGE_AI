import MetaTrader5 as mt5
import pandas as pd
import time
import csv
import os
from datetime import datetime

# =========================
# CONFIG
# =========================
SYMBOL = "Volatility 75 (1s) Index"
TIMEFRAME = mt5.TIMEFRAME_M1

RISK_PERCENT = 1
SL_POINTS = 50
TP_POINTS = 100
DEVIATION = 50

COOLDOWN_SECONDS = 10
last_trade_time = 0

LOG_FILE = "trade_log.csv"

# =========================
# INIT / FIX LOG FILE
# =========================
def init_log():
    headers = [
        "Ticket","Time","Type","Lot",
        "Entry","SL","TP",
        "Exit","Profit","Status"
    ]

    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", newline="") as f:
            csv.writer(f).writerow(headers)
    else:
        df = pd.read_csv(LOG_FILE)

        # Auto-fix wrong format
        if "Ticket" not in df.columns:
            print("⚠️ Fixing old log format...")
            with open(LOG_FILE, "w", newline="") as f:
                csv.writer(f).writerow(headers)

# =========================
# CONNECT
# =========================
def connect():
    if not mt5.initialize():
        print("❌ MT5 connection failed")
        return False
    print("✅ MT5 Connected")
    return True

# =========================
# GET DATA
# =========================
def get_data():
    rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, 100)
    return pd.DataFrame(rates) if rates is not None else None

# =========================
# STRATEGY (SMC + BOS)
# =========================
def strategy(df):
    recent = df.tail(20)

    high = recent['high'].max()
    low = recent['low'].min()

    last = df.iloc[-1]
    prev = df.iloc[-2]

    print(f"📦 Range: {high} - {low}")

    sweep_sell = prev['high'] > high
    sweep_buy = prev['low'] < low

    bos_sell = last['low'] < prev['low']
    bos_buy = last['high'] > prev['high']

    if sweep_sell and bos_sell:
        print("💣 SELL setup")
        return "SELL"

    if sweep_buy and bos_buy:
        print("💣 BUY setup")
        return "BUY"

    return None

# =========================
# LOT SIZE
# =========================
def lot_size():
    acc = mt5.account_info()
    sym = mt5.symbol_info(SYMBOL)

    risk = acc.balance * (RISK_PERCENT / 100)
    lot = sym.volume_min + (risk / 1000)

    return round(max(sym.volume_min, min(lot, sym.volume_max)), 3)

# =========================
# LOG TRADE
# =========================
def log_trade(ticket, typ, lot, entry, sl, tp):
    with open(LOG_FILE, "a", newline="") as f:
        csv.writer(f).writerow([
            ticket, datetime.now(), typ, lot,
            entry, sl, tp,
            "", "", "OPEN"
        ])

# =========================
# UPDATE CLOSED TRADES
# =========================
def update_trades():
    try:
        df = pd.read_csv(LOG_FILE)
    except:
        return

    deals = mt5.history_deals_get(datetime(2024,1,1), datetime.now())
    if deals is None:
        return

    for d in deals:
        if d.entry == 1:  # exit
            ticket = d.position_id

            if ticket in df["Ticket"].values:
                idx = df[df["Ticket"] == ticket].index[0]

                if df.loc[idx, "Status"] == "OPEN":
                    df.loc[idx, "Exit"] = d.price
                    df.loc[idx, "Profit"] = d.profit
                    df.loc[idx, "Status"] = "CLOSED"

    df.to_csv(LOG_FILE, index=False)

# =========================
# ANALYTICS
# =========================
def analytics():
    try:
        df = pd.read_csv(LOG_FILE)
    except:
        return

    closed = df[df["Status"] == "CLOSED"]

    if len(closed) == 0:
        print("📊 No closed trades yet\n")
        return

    total = len(closed)
    wins = len(closed[closed["Profit"] > 0])
    losses = len(closed[closed["Profit"] <= 0])

    profit = closed["Profit"].sum()
    winrate = (wins / total) * 100

    print("\n📊 PERFORMANCE")
    print(f"Trades: {total}")
    print(f"Wins: {wins} | Losses: {losses}")
    print(f"Winrate: {winrate:.2f}%")
    print(f"Profit: {profit:.2f}\n")

# =========================
# PLACE TRADE
# =========================
def place_trade(signal):
    global last_trade_time

    tick = mt5.symbol_info_tick(SYMBOL)
    lot = lot_size()

    price = tick.ask if signal == "BUY" else tick.bid

    sl = price - SL_POINTS if signal == "BUY" else price + SL_POINTS
    tp = price + TP_POINTS if signal == "BUY" else price - TP_POINTS

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": lot,
        "type": mt5.ORDER_TYPE_BUY if signal=="BUY" else mt5.ORDER_TYPE_SELL,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": DEVIATION,
        "magic": 123456
    }

    result = mt5.order_send(request)

    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        print("✅ Trade placed")
        log_trade(result.order, signal, lot, price, sl, tp)
        last_trade_time = time.time()
    else:
        print("❌ Trade failed")

# =========================
# MAIN LOOP
# =========================
def run():
    global last_trade_time

    init_log()
    connect()

    print("🚀 Analytics Bot Running...\n")

    while True:
        df = get_data()
        if df is None:
            time.sleep(1)
            continue

        update_trades()
        analytics()

        if mt5.positions_total() == 0:
            signal = strategy(df)

            if signal and (time.time() - last_trade_time > COOLDOWN_SECONDS):
                place_trade(signal)
        else:
            print("⚠️ Position open\n")

        time.sleep(2)

# =========================
# START
# =========================
if __name__ == "__main__":
    run()