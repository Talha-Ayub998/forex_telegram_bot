import MetaTrader5 as mt5
from time import sleep
import logging
import threading

# Function to initialize MetaTrader 5 connection

logging.basicConfig(filename='break_even_trailing.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def initialize_meta_trader(path, login, password, servername):
    try:
        if not mt5.initialize(path=path, login=login, password=password, server=servername):
            logging.error(f"initialize() failed for login {login}, error code = {mt5.last_error()}")
            return False
        logging.info(f"MetaTrader 5 Initialized Successfully for login {login}.")
        return True
    except Exception as e:
        logging.error(f"Error initializing MetaTrader 5 for login {login}: {e}")
        return False

# Function to modify SL and TP for an existing order


def modify_sl_tp(order_id, sl=None, tp=None):
    try:
        position = mt5.positions_get(ticket=order_id)
        if position:
            position = position[0]
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": position.symbol,
                "position": order_id,
                "tp": tp if tp is not None else position.tp,
                "sl": sl if sl is not None else position.sl,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC
            }
            result = mt5.order_send(request)
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                logging.info(f"Order {order_id} updated successfully: SL={request['sl']}, TP={request['tp']}")
            else:
                logging.info(f"Failed to modify order {order_id}: {result.comment} (Retcode: {result.retcode})")
        else:
            logging.info(f"Position with ID {order_id} not found.")
    except Exception as e:
        logging.info(f"Error modifying order {order_id}: {e}")



# Function to adjust buy position SL dynamically based on 50% of distance to TP
def adjust_buy_position(position, current_price):

    distance_to_tp = position.tp - position.price_open
    distance_to_current = current_price - position.price_open

    if distance_to_current >= 0.50 * distance_to_tp:
        new_sl = position.price_open + 0.18 * distance_to_tp

        if round(position.sl, 2) != round(new_sl, 2):
            modify_sl_tp(position.ticket, sl=new_sl)
            logging.info(f"Buy position: SL updated to {new_sl}")


# Function to adjust sell position SL dynamically based on 50% of distance to TP
def adjust_sell_position(position, current_price):

    distance_to_tp = position.price_open - position.tp
    distance_to_current = position.price_open - current_price

    if distance_to_current >= 0.50 * distance_to_tp:
        new_sl = position.price_open - 0.18 * distance_to_tp

        if round(position.sl, 2) != round(new_sl, 2):
            modify_sl_tp(position.ticket, sl=new_sl)
            logging.info(f"Sell position: SL updated to {new_sl}")


def monitor_positions():
    while True:
        positions = mt5.positions_get()
        if positions:
            # logging.info(f"Total number of positions now:{positions}")
            for position in positions:
                current_price = (
                    mt5.symbol_info_tick(position.symbol).ask
                    if position.type == mt5.ORDER_TYPE_BUY
                    else mt5.symbol_info_tick(position.symbol).bid
                )
                if position.type == mt5.ORDER_TYPE_BUY:
                    adjust_buy_position(position, current_price)
                elif position.type == mt5.ORDER_TYPE_SELL:
                    adjust_sell_position(position, current_price)
        # else:
        #     logging(f"No open positions for account {login}.")
        sleep(5)  # Wait before next check

# Main entry point
if __name__ == "__main__":
    LOGIN = 52154359
    SERVER = 'ICMarketsSC-Demo'
    PASSWORD = 'gA24C@Au6xs7zh'
    PATH = 'C:\\Program Files\\MetaTrader 5 IC Markets Global\\terminal64.exe'

    if initialize_meta_trader(PATH, int(LOGIN), PASSWORD, SERVER):
        logging.info(f"Starting to monitor positions for account {LOGIN}...")
        monitor_positions()
        while True:
            try:
                sleep(1)  # Keep the main thread alive
            except KeyboardInterrupt:
                logging.error(f"Shutting down monitoring...")
                mt5.shutdown()  # Cleanly shutdown MT5
                break
    else:
        logging.error(f"Failed to initialize MetaTrader 5 for account {LOGIN}.")
