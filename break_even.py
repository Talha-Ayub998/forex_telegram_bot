import MetaTrader5 as mt5
from time import sleep
from datetime import datetime

# Function to initialize MetaTrader 5 connection


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

# Function to modify SL and TP for an existing order


def modify_sl_tp(order_id, sl=None, tp=None):
    try:
        # Prepare modification request
        position = mt5.positions_get(ticket=order_id)
        if position:
            position = position[0]
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": position.symbol,
                "position": order_id,
                "tp": tp if tp is not None else position.tp,
                "sl": 2728.07,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC
            }
            result = mt5.order_send(request)
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"Order {order_id} updated successfully: SL={request['sl']}, TP={request['tp']}")
            else:
                print(f"Failed to modify order {order_id}: {result.comment} (Retcode: {result.retcode})")
        else:
            print(f"Position with ID {order_id} not found.")
    except Exception as e:
        print(f"Error modifying order {order_id}: {e}")

# Function to adjust buy position SL dynamically based on 75% of distance to TP


def adjust_buy_position(position, current_price):
    """Adjust SL/TP for a buy position dynamically."""
    distance_to_tp = position.tp - position.price_open
    distance_to_current = current_price - position.price_open

    # If the price reaches 75% towards TP, update SL to break-even (25% from entry price)
    if distance_to_current >= 0.75 * distance_to_tp and position.sl != position.price_open + 0.25 * distance_to_tp:
        # Set SL to 25% from the entry price
        new_sl = position.price_open + 0.25 * distance_to_tp
        modify_sl_tp(position.ticket, sl=new_sl)
        print(f"Buy position: SL updated to {new_sl} & distance_to_current:{distance_to_current} & 75% {0.75 * distance_to_tp}")

# Function to adjust sell position SL dynamically based on 75% of distance to TP


def adjust_sell_position(position, current_price):
    """Adjust SL/TP for a sell position dynamically based on 75% of distance to TP."""
    distance_to_tp = position.price_open - position.tp
    distance_to_current = position.price_open - current_price

    # If the price reaches 75% towards TP, update SL to break-even (25% from entry price)
    if distance_to_current >= 0.75 * distance_to_tp and position.sl != position.price_open - 0.25 * distance_to_tp:
        # Set SL to 25% from the entry price
        new_sl = position.price_open - 0.25 * distance_to_tp
        modify_sl_tp(position.ticket, sl=new_sl)
        print(f"Sell position: SL updated to {new_sl} & distance_to_current:{distance_to_current} & 75% {0.75 * distance_to_tp}")
# Function to handle continuous check for position SL and TP updates


def monitor_positions():
    while True:
        # Get all open positions
        positions = mt5.positions_get()
        if positions:
            for position in positions:
                current_price = mt5.symbol_info_tick(
                    position.symbol).ask if position.type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(position.symbol).bid
                # Check and update Buy positions
                if position.type == mt5.ORDER_TYPE_BUY:
                    adjust_buy_position(position, current_price)
                # Check and update Sell positions
                elif position.type == mt5.ORDER_TYPE_SELL:
                    adjust_sell_position(position, current_price)
        else:
            print("No open positions.")
        sleep(5)  # Wait for 1 second before checking again


if __name__ == "__main__":
    LOGIN = 52114068
    SERVER = 'ICMarketsSC-Demo'
    PASSWORD = 'ska6kwS&k&$dnQ'
    PATH = 'C:\\Program Files\\MetaTrader 5 IC Markets Global\\terminal64.exe'

    if initialize_meta_trader(PATH, LOGIN, PASSWORD, SERVER):
        print("Starting to monitor positions...")
        monitor_positions()  # Start monitoring positions
