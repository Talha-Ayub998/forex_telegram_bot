import MetaTrader5 as mt5
import pandas as pd
import logging
import time
from datetime import datetime

# === CONFIG ===
LOGIN = 52285388
SERVER = 'ICMarketsSC-Demo'
PASSWORD = 'Jmd!4aT$eg!rsa'
PATH = 'C:\\Program Files\\MetaTrader 5 IC Markets Global\\terminal64.exe'

SYMBOL = "GBPJPY"
TIMEFRAME = mt5.TIMEFRAME_M5
LOT_SIZE = 0.2
CONTRACT_SIZE = 100
MA_LENGTH = 200
INITIAL_SL_OFFSET = 3
TP_PCT = 0.01

# === LOGGING SETUP ===
logging.basicConfig(filename="live_mt5_GBPJPY.log", level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")

# === INIT MT5 ===
def initialize_mt5():
    if not mt5.initialize(path=PATH, login=LOGIN, password=PASSWORD, server=SERVER):
        logging.error(f"MT5 init failed: {mt5.last_error()}")
        raise SystemExit("MT5 initialization failed")
    logging.info("✅ MT5 Initialized")

# === GET MARKET DATA ===
def fetch_candles(symbol, timeframe, bars=MA_LENGTH + 10):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df

# === DETECT SMA SIGNAL ===
def detect_sma_crossover(df):
    df['sma'] = df['close'].rolling(MA_LENGTH).mean()
    current = df.iloc[-1]
    prev = df.iloc[-2]

    if prev['low'] < prev['sma'] and current['close'] > current['sma'] and current['close'] > current['open'] and current['low'] > current['sma']:
        return "BUY", current
    elif prev['high'] > prev['sma'] and current['close'] < current['sma'] and current['close'] < current['open'] and current['high'] < current['sma']:
        return "SELL", current
    return None, None

# === PLACE ORDER ===
def place_order(symbol, action, entry_price, sl, tp, comment):
    order_type = mt5.ORDER_TYPE_BUY if action == "BUY" else mt5.ORDER_TYPE_SELL
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": LOT_SIZE,
        "type": order_type,
        "price": entry_price,
        "sl": sl,
        # "tp": tp,  # manually handled, not sent
        "magic": 20052025,
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
        "deviation": 10,
    }

    # Send order
    result = mt5.order_send(request)

    if result is None:
        logging.error("❌ order_send returned None — MT5 rejected the request.")
        logging.error(f"📋 Last MT5 Error: {mt5.last_error()}")
        logging.error("📝 Request sent:")
        for key, value in request.items():
            logging.error(f"  {key}: {value}")
        return

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logging.error(f"❌ Order failed with retcode: {result.retcode} — {result.comment}")
        logging.error("📝 Request sent:")
        for key, value in request.items():
            logging.error(f"  {key}: {value}")
        logging.error("📋 Full result object:")
        logging.error(str(result))
    else:
        order_ticket = result.order
        logging.info("✅ Order placed successfully:")
        logging.info(f"  Ticket: {order_ticket}")
        logging.info(f"  Entry Price: {entry_price}")
        logging.info(f"  SL: {sl}")
        logging.info(f"  TP: None (manual monitor)")
        logging.info(f"  Volume: {LOT_SIZE}")
        logging.info(f"  Type: {action}")


# === MAIN LOOP ===
def run_strategy():
    last_signal_time = None

    while True:
        df = fetch_candles(SYMBOL, TIMEFRAME)
        if df.empty or len(df) < MA_LENGTH + 2:
            logging.warning("Not enough bars to compute SMA.")
            time.sleep(30)
            continue

        signal, candle = detect_sma_crossover(df)
        signal_time = candle['time'].strftime("%Y-%m-%d %H:%M") if candle is not None else None

        if signal and signal_time != last_signal_time:
            entry_price = mt5.symbol_info_tick(SYMBOL).ask if signal == "BUY" else mt5.symbol_info_tick(SYMBOL).bid
            sl = candle['low'] - INITIAL_SL_OFFSET if signal == "BUY" else candle['high'] + INITIAL_SL_OFFSET
            tp = entry_price + entry_price * TP_PCT if signal == "BUY" else entry_price - entry_price * TP_PCT
            place_order(SYMBOL, signal, entry_price, sl, tp, f"{signal_time} SMA Crossover")
            last_signal_time = signal_time
        else:
            logging.info("No signal or already processed.")

        time.sleep(60)

# === ENTRY POINT ===
if __name__ == "__main__":
    initialize_mt5()
    run_strategy()
