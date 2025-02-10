import logging
import json
import threading
import os
from datetime import datetime, timezone

import MetaTrader5 as mt5
from flask import Flask, request, jsonify

app = Flask(__name__)

# Configure logging
logging.basicConfig(filename='app.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def initialize_meta_trader(path, login, password, servername):
    try:
        if not mt5.initialize(path=path, login=login, password=password, server=servername):
            logging.error(f"initialize() failed, error code = {mt5.last_error()}")
            return False
        return True
    except Exception as e:
        logging.error(f"Error initializing MetaTrader5: {e}")
        return False

def log_order_to_file(order_details, file_name):
    try:
        try:
            with open(file_name, "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            data = []
        data.append(order_details)
        with open(file_name, "w") as f:
            json.dump(data, f, indent=4)
        logging.info(f"Order logged successfully: {order_details}")
    except Exception as e:
        logging.error(f"Failed to log order: {e}")

def save_mapping(current_order_id, pending_order_id, symbol, action, timeframe, entry_price, pending_entry_price, pending_order_type):
    try:
        file_name = f"{symbol}_order_mapping.json"
        mapping = {
            "current_order_id": current_order_id,
            "pending_order_id": pending_order_id,
            "symbol": symbol,
            "current_action": action,
            "pending_action": pending_order_type,
            "timeframe": timeframe,
            "current_entry_price": entry_price,
            "pending_entry_price": pending_entry_price,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        }
        if os.path.exists(file_name):
            try:
                with open(file_name, "r") as file:
                    data = json.load(file)
            except json.JSONDecodeError:
                data = []
        else:
            data = []
        data.append(mapping)
        with open(file_name, "w") as file:
            json.dump(data, file, indent=4)
        logging.info(f"Order mapping saved: {mapping}")
    except Exception as e:
        logging.error(f"Error saving order mapping: {e}")

def place_order_with_pending(symbol, action, timeframe, low_price):
    try:
        entry_price = mt5.symbol_info_tick(symbol).ask if action == "buy" else mt5.symbol_info_tick(symbol).bid
        ###########################################
        # CURRENT ORDER DETAILS
        ###########################################
        if action == "buy":
            current_order_type = mt5.ORDER_TYPE_BUY

            # Below We are setting sl here like (-1) for buy
            sl = low_price - 1

            # The tp we add depends on the timeframe:
            # - If the timeframe is 10 or 15, we add 29 units.
            # - If the timeframe is 5, we add 24 units.
            # - For any other timeframe, we add 19 units.
            tp = entry_price + (29 if timeframe in [10, 15] else 24 if timeframe == 5 else 19)

        elif action == "sell":
            current_order_type = mt5.ORDER_TYPE_SELL

            # Below We are setting sl here like (+1) for sell
            sl = low_price + 1

            # The tp we subtract depends on the timeframe:
            # - If the timeframe is 10 or 15, we subtract 29 units.
            # - If the timeframe is 5, we subtract 24 units.
            # - For any other timeframe, we subtract 19 units.
            tp = entry_price - (29 if timeframe in [10, 15] else 24 if timeframe == 5 else 19)
        else:
            logging.error("Invalid order type")
            return
        lot_size = 0.3
        ###########################################
        # END CURRENT ORDER DETAILS
        ###########################################

        # Place current market order
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot_size,
            "type": current_order_type,
            "price": entry_price,
            "sl": float(sl),
            "tp": float(tp),
            "magic": 123456,
            "comment": f"Current RSI Signal-{timeframe}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        logging.info(f"Placing current market order: {request}")
        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            current_order_id = result.order
            logging.info(f"Current order successfully placed: {current_order_id}")
            ###########################################
            # PENDING ORDER DETAILS
            ###########################################
            if action == "buy":
                pending_order_type = mt5.ORDER_TYPE_SELL_STOP
                pending_entry_price = sl

                # Below We are setting pending_sl here like (+10) for buy
                pending_sl = pending_entry_price + 10

                # The pending_tp we subtract depends on the timeframe:
                # - If the timeframe is 10 or 15, we subtract 29 units.
                # - If the timeframe is 5, we subtract 24 units.
                # - For any other timeframe, we subtract 19 units.
                pending_tp = pending_entry_price - (29 if timeframe in [10, 15] else 24 if timeframe == 5 else 19)
            elif action == "sell":
                pending_order_type = mt5.ORDER_TYPE_BUY_STOP
                pending_entry_price = sl

                # Below We are setting pending_sl here like (-10) for sell
                pending_sl = pending_entry_price - 10

                # The pending_tp we add depends on the timeframe:
                # - If the timeframe is 10 or 15, we add 29 units.
                # - If the timeframe is 5, we add 24 units.
                # - For any other timeframe, we add 19 units.
                pending_tp = pending_entry_price + (29 if timeframe in [10, 15] else 24 if timeframe == 5 else 19)

            ###########################################
            # END PENDING ORDER DETAILS
            ###########################################

            # Place the pending order
            pending_request = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": symbol,
                "volume": lot_size,
                "type": pending_order_type,
                "price": float(pending_entry_price),
                "sl": float(pending_sl),
                "tp": float(pending_tp),
                "magic": 123456,
                "comment": f"Pending RSI Signal-{timeframe}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            logging.info(f"Placing pending order: {pending_request}")
            pending_result = mt5.order_send(pending_request)
            if pending_result.retcode == mt5.TRADE_RETCODE_DONE:
                pending_order_id = pending_result.order
                logging.info(f"Pending order successfully placed: {pending_order_id}")
                save_mapping(
                    current_order_id=current_order_id,
                    pending_order_id=pending_order_id,
                    symbol=symbol,
                    action=action,
                    timeframe=timeframe,
                    entry_price=entry_price,
                    pending_entry_price=pending_entry_price,
                    pending_order_type=pending_order_type
                )
            else:
                logging.error(f"Failed to place pending order: {pending_result.retcode}")
        else:
            logging.error(f"Failed to place current order: {result.retcode}")
    except Exception as e:
        logging.error(f"Error placing order: {e}")

LOGIN = 52154359
SERVER = 'ICMarketsSC-Demo'
PASSWORD = 'gA24C@Au6xs7zh'
PATH = 'C:\\Program Files\\MetaTrader 5 IC Markets Global\\terminal64.exe'
initialize_meta_trader(PATH, int(LOGIN), PASSWORD, SERVER)

@app.route('/test', methods=['GET'])
def test():
    return jsonify({"status": "success"}), 200

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        logging.info(f"Received alert: {data}")

        symbol = data.get("ticker")
        action = data.get("trade").lower()
        timeframe = int(data.get('time_frame'))
        low_price = float(data.get('price'))

        order_thread = threading.Thread(target=place_order_with_pending, args=(symbol, action, timeframe, low_price))
        order_thread.start()

        logging.info(f"Order process started for {symbol} {action} on {timeframe}M timeframe.")
        return jsonify({"status": "success"}), 200
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(port=5000, debug=True)
