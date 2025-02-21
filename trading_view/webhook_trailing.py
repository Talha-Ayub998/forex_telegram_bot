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


def place_market_order(symbol, action, volume, price, sl, tp, comment):
    """Function to place a market order."""
    order_type = mt5.ORDER_TYPE_BUY if action == "buy" else mt5.ORDER_TYPE_SELL

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": price,
        "sl": float(sl),
        "tp": float(tp),
        "magic": 123456,
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    logging.info(f"Placing {action} order: {request}")
    result = mt5.order_send(request)

    if result.retcode == mt5.TRADE_RETCODE_DONE:
        logging.info(f"Order placed successfully: {result.order}")
        return result.order
    else:
        logging.error(f"Failed to place order: {result.retcode}")
        return None


def place_order(symbol, action, timeframe, low_price):
    """Main function to place initial order and split into two take profits."""
    try:
        entry_price = mt5.symbol_info_tick(symbol).ask if action == "buy" else mt5.symbol_info_tick(symbol).bid
        lot_size = 0.1  # Example lot size

        if action == "buy":
            sl = low_price - 10
            tp1 = entry_price + 3
            tp2 = entry_price + 6
        elif action == "sell":
            sl = low_price + 10
            tp1 = entry_price - 3
            tp2 = entry_price - 6
        else:
            logging.error("Invalid action type")
            return

        # Place first order for TP1
        order1 = place_market_order(symbol, action, lot_size / 2, entry_price, sl, tp1, f"{timeframe}-RSI TP1")

        # Place second order for TP2
        order2 = place_market_order(symbol, action, lot_size / 2, entry_price, sl, tp2, f"{timeframe}-RSI TP2")

        if order1 and order2:
            logging.info(f"Both TP1 and TP2 orders placed successfully: {order1}, {order2}")
        else:
            logging.error("Failed to place one or both TP orders.")

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
