import MetaTrader5 as mt5
import time
import logging

# === CONFIG ===
LOGIN = 52285388
SERVER = 'ICMarketsSC-Demo'
PASSWORD = 'Jmd!4aT$eg!rsa'
PATH = 'C:\\Program Files\\MetaTrader 5 IC Markets Global\\terminal64.exe'

SYMBOL = "XAUUSD"
LOT_SIZE = 0.2
CONTRACT_SIZE = 100
PROFIT_TARGET_PCT = 0.01
SL_MOVE_TRIGGER = 2
SL_AFTER_MOVE = 1

# === LOGGING ===
logging.basicConfig(filename="monitor_trades.log", level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")

def initialize_mt5():
    if not mt5.initialize(path=PATH, login=LOGIN, password=PASSWORD, server=SERVER):
        logging.error(f"MT5 init failed: {mt5.last_error()}")
        raise SystemExit("MT5 initialization failed")
    logging.info("✅ MT5 Initialized (Monitor Mode)")

def monitor_open_trades():
    moved_sl_tickets = set()  # to track SL movement only once per ticket

    while True:
        positions = mt5.positions_get(symbol=SYMBOL)
        if not positions:
            logging.info("No open positions. Waiting...")
            time.sleep(10)
            continue

        account_info = mt5.account_info()
        balance = account_info.balance

        for pos in positions:
            entry_price = pos.price_open
            ticket = pos.ticket
            action = "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL"
            volume = pos.volume
            current_sl = pos.sl
            current_price = mt5.symbol_info_tick(SYMBOL).bid if action == "SELL" else mt5.symbol_info_tick(SYMBOL).ask

            # === Floating profit calculation ===
            floating_profit = (current_price - entry_price) * volume * CONTRACT_SIZE if action == "BUY" else (entry_price - current_price) * volume * CONTRACT_SIZE

            # === Floating TP Exit ===
            if floating_profit >= balance * PROFIT_TARGET_PCT:
                logging.info(f"📈 Closing ticket {ticket} - floating profit hit: {floating_profit}")

                close_type = mt5.ORDER_TYPE_SELL if action == "BUY" else mt5.ORDER_TYPE_BUY
                close_result = mt5.order_send({
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": SYMBOL,
                    "volume": volume,
                    "type": close_type,
                    "position": ticket,
                    "price": current_price,
                    "deviation": 10,
                    "magic": 20052025,
                    "comment": "Manual TP hit",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC
                })

                if close_result.retcode == mt5.TRADE_RETCODE_DONE:
                    logging.info(f"✅ Trade closed at {current_price}")
                else:
                    logging.error(f"❌ Failed to close trade: {close_result.comment}")
                continue  # move to next position

            # === SL Move Logic (one-time only per position) ===
            if ticket not in moved_sl_tickets:
                sl_update_needed = False

                if action == "BUY" and current_price >= entry_price + SL_MOVE_TRIGGER:
                    new_sl = entry_price + SL_AFTER_MOVE
                    if not current_sl or new_sl > current_sl:
                        sl_update_needed = True

                elif action == "SELL" and current_price <= entry_price - SL_MOVE_TRIGGER:
                    new_sl = entry_price - SL_AFTER_MOVE
                    if not current_sl or new_sl < current_sl:
                        sl_update_needed = True

                if sl_update_needed:
                    result = mt5.order_send({
                        "action": mt5.TRADE_ACTION_SLTP,
                        "symbol": SYMBOL,
                        "position": ticket,
                        "sl": new_sl,
                        "tp": 0.0,
                        "deviation": 10,
                        "magic": 20052025,
                        "comment": "SL Moved",
                        "type_time": mt5.ORDER_TIME_GTC,
                        "type_filling": mt5.ORDER_FILLING_IOC
                    })

                    if result.retcode == mt5.TRADE_RETCODE_DONE:
                        logging.info(f"🔁 SL moved to {new_sl} for ticket {ticket}")
                        moved_sl_tickets.add(ticket)
                    else:
                        logging.warning(f"⚠️ Failed to move SL for ticket {ticket}: {result.comment}")

        time.sleep(10)

if __name__ == "__main__":
    initialize_mt5()
    monitor_open_trades()
