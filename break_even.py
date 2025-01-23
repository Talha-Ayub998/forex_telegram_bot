import MetaTrader5 as mt5
from time import sleep
from threading import Thread

# Function to initialize MetaTrader 5 connection


def initialize_meta_trader(path, login, password, servername):
    try:
        if not mt5.initialize(path=path, login=login, password=password, server=servername):
            print(f"initialize() failed for login {login}, error code = {mt5.last_error()}")
            return False
        print(f"MetaTrader 5 Initialized Successfully for login {login}.")
        return True
    except Exception as e:
        print(f"Error initializing MetaTrader 5 for login {login}: {e}")
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
                print(f"Order {order_id} updated successfully: SL={request['sl']}, TP={request['tp']}")
            else:
                print(f"Failed to modify order {order_id}: {result.comment} (Retcode: {result.retcode})")
        else:
            print(f"Position with ID {order_id} not found.")
    except Exception as e:
        print(f"Error modifying order {order_id}: {e}")

# Function to adjust buy position SL dynamically based on 75% of distance to TP


def adjust_buy_position(position, current_price):
    distance_to_tp = position.tp - position.price_open
    distance_to_current = current_price - position.price_open
    if distance_to_current >= 0.75 * distance_to_tp and position.sl != position.price_open + 0.25 * distance_to_tp:
        new_sl = position.price_open + 0.25 * distance_to_tp
        modify_sl_tp(position.ticket, sl=new_sl)
        print(f"Buy position: SL updated to {new_sl}")

# Function to adjust sell position SL dynamically based on 75% of distance to TP


def adjust_sell_position(position, current_price):
    distance_to_tp = position.price_open - position.tp
    distance_to_current = position.price_open - current_price
    if distance_to_current >= 0.75 * distance_to_tp and position.sl != position.price_open - 0.25 * distance_to_tp:
        new_sl = position.price_open - 0.25 * distance_to_tp
        modify_sl_tp(position.ticket, sl=new_sl)
        print(f"Sell position: SL updated to {new_sl}")


def monitor_positions(path, login, password, servername):
    if initialize_meta_trader(path, login, password, servername):
        print(f"Starting to monitor positions for account {login}...")
        while True:
            positions = mt5.positions_get()
            if positions:
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
            #     print(f"No open positions for account {login}.")
            sleep(5)  # Wait before next check
    else:
        print(f"Failed to initialize MetaTrader 5 for account {login}.")


if __name__ == "__main__":
    accounts = [
        {"login": 52114068, "password": 'ska6kwS&k&$dnQ', "server": 'ICMarketsSC-Demo',
          "path": 'C:\\Program Files\\MetaTrader 5 IC Markets Global\\terminal64.exe'},

        {"login": 61303556, "password": 'cTCXW#3T3pz2@bj', "server": 'Pepperstone-Demo',
          "path": 'C:\\Program Files\\Pepperstone MetaTrader 5\\terminal64.exe'}
    ]

    threads = []
    for account in accounts:
        print(f"Starting thread for account {account['login']}")
        thread = Thread(target=monitor_positions, args=(account["path"], account["login"], account["password"], account["server"]))
        thread.start()
        threads.append(thread)


    for thread in threads:
        thread.join()  # Wait for all threads to complete
    import threading
    print(f"Active threads: {threading.active_count()}")
