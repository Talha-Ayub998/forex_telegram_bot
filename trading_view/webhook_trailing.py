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

def place_order(symbol, action, timeframe, low_price):
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
            "comment": f"{timeframe}-RSI Signal",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        logging.info(f"Placing current market order: {request}")
        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            current_order_id = result.order
            logging.info(f"Current order successfully placed: {current_order_id}")
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

        order_thread = threading.Thread(target=place_order, args=(symbol, action, timeframe, low_price))
        order_thread.start()

        logging.info(f"Order process started for {symbol} {action} on {timeframe}M timeframe.")
        return jsonify({"status": "success"}), 200
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(port=5000, debug=True)
