import MetaTrader5 as mt5
from time import sleep
import os
import json
import logging
import threading

# Configure logging
logging.basicConfig(filename='break_even.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize MetaTrader 5 connection
def initialize_meta_trader(path, login, password, servername):
    try:
        if not mt5.initialize(path=path, login=login, password=password, server=servername):
            print(f"initialize() failed, error code = {mt5.last_error()}")
            return False
        print("MetaTrader 5 Initialized Successfully.")
        return True
    except Exception as e:
        print(f"Error initializing MetaTrader 5: {e}")
        return False

# Apply break-even stop loss
def apply_break_even(position, current_price, entry_price, symbol, action):
    try:
        new_sl = entry_price
        request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": position.symbol,
                "position": position.ticket,
                "tp": position.tp,
                "sl": new_sl,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC
            }
        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"Break-even SL applied: {new_sl} for order {position.ticket}")
            cancel_pending_order(symbol, position.ticket)
        else:
            print(f"Failed to update SL for order {position.ticket}, error code: {result.retcode}")
    except Exception as e:
        print(f"Error applying break-even: {e}")

# Cancel the pending order associated with the current order
def cancel_pending_order(symbol, current_order_id):
    file_name = f"{symbol}_order_mapping.json"
    if not os.path.exists(file_name):
        print(f"Mapping file not found: {file_name}")
        return

    try:
        with open(file_name, "r") as file:
            data = json.load(file)

        mapping = next((item for item in data if item["current_order_id"] == current_order_id), None)
        if not mapping:
            print(f"No mapping found for current order ID {current_order_id}")
            return

        pending_order_id = mapping["pending_order_id"]
        request = {"action": mt5.TRADE_ACTION_REMOVE, "order": pending_order_id}
        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"Pending order {pending_order_id} successfully canceled.")

            updated_data = [item for item in data if item["current_order_id"] != current_order_id]
            with open(file_name, "w") as file:
                json.dump(updated_data, file, indent=4)
            print(f"Order {current_order_id} and its pending order removed from mapping.")
        else:
            print(f"Failed to cancel pending order {pending_order_id}, error code: {result.retcode}")
    except Exception as e:
        print(f"Error canceling pending order for order {current_order_id}: {e}")

# Monitor open positions for break-even conditions
def monitor_positions():
    while True:
        positions = mt5.positions_get()
        if positions:
            for position in positions:
                if position.sl == position.price_open:
                    # logging.info(f"Skipping position {position.ticket}: SL:{position.sl} already at entry price:{position.price_open}.")
                    continue

                current_price = mt5.symbol_info_tick(position.symbol).ask if position.type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(position.symbol).bid
                entry_price = position.price_open

                if position.type == mt5.ORDER_TYPE_BUY and current_price >= entry_price + 8:
                    apply_break_even(position, current_price, entry_price, position.symbol, "buy")
                elif position.type == mt5.ORDER_TYPE_SELL and current_price <= entry_price - 8:
                    apply_break_even(position, current_price, entry_price, position.symbol, "sell")
        # else:
        #     print("No open positions.")
        sleep(5)

# Run monitoring in a separate thread
def start_monitoring():
    monitor_thread = threading.Thread(target=monitor_positions, daemon=True)
    monitor_thread.start()
    print("Monitoring started in a background thread.")

# Main entry point
if __name__ == "__main__":
    LOGIN = 241273863
    SERVER = 'Exness-MT5Trial'
    PASSWORD = 'Panda_22'
    PATH = 'C:\\Program Files\\MetaTrader 5 EXNESS\\terminal64.exe'

    if initialize_meta_trader(PATH, int(LOGIN), PASSWORD, SERVER):
        start_monitoring()
        while True:
            try:
                sleep(1)  # Keep the main thread alive
            except KeyboardInterrupt:
                print("Shutting down monitoring...")
                mt5.shutdown()  # Cleanly shutdown MT5
                break
