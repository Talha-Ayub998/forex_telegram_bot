from flask import Flask, request, jsonify
import logging
import json
import MetaTrader5 as mt5
import time

app = Flask(__name__)

# Configure logging
logging.basicConfig(filename='app.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def initialize_meta_trader(path, login, password, servername):
    try:
        if not mt5.initialize(path=path, login=login, password=password, server=servername):
            print(f"initialize() failed, error code = {mt5.last_error()}")
            return False
        return True
    except Exception as e:
        print(f"Error initializing MetaTrader5: {e}")
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
        print(f"Order logged successfully: {order_details}")
    except Exception as e:
        print(f"Failed to log order: {e}")

def place_order(symbol, action, timeframe):
    try:
        if action == "buy":
            order_type = mt5.ORDER_TYPE_BUY
        elif action == "sell":
            order_type = mt5.ORDER_TYPE_SELL
        else:
            print("Invalid order type")
            return

        lot_size = 0.1
        price = mt5.symbol_info_tick(symbol).ask if action == "buy" else mt5.symbol_info_tick(symbol).bid
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot_size,
            "type": order_type,
            "price": price,
            "magic": 123456,
            "comment": f"RSI Signal-{timeframe}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        print("The request is:", request)
        result = mt5.order_send(request)

        if result.retcode == mt5.TRADE_RETCODE_DONE:
            order_details = {
                "order_id": result.order,
                "symbol": symbol,
                "action": action,
                "timeframe": timeframe,
                "volume": lot_size,
                "price": price,
                "comment": f"RSI Signal-{timeframe}",
                "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            print(f"Order Opened: {order_details}")
            log_order_to_file(order_details, file_name=f"{symbol}_orders_log.json")
        else:
            print(f"Failed to place order: {result.retcode}")
            failed_order_details = {
                "symbol": symbol,
                "action": action,
                "timeframe": timeframe,
                "volume": lot_size,
                "price": price,
                "comment": f"RSI Signal-{timeframe}",
                "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "error": result.retcode,
            }
            log_order_to_file(failed_order_details, f"{symbol}_failed_orders_log.json") 
    except Exception as e:
        print(f"Error placing order: {e}")


LOGIN = 241273863
SERVER = 'Exness-MT5Trial'
PASSWORD = 'Panda_22'
PATH = 'C:\\Program Files\\MetaTrader 5 EXNESS\\terminal64.exe'
initialize_meta_trader(PATH, int(LOGIN), PASSWORD, SERVER)

@app.route('/test', methods=['GET'])
def test():
    return jsonify({"status": "success"}), 200


@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        logging.info(f"Received alert: {data}")

        symbol = data.get("ticker")+'m'
        action = data.get("trade").lower()
        timeframe = data.get('time_frame')

        # Call place_order function (implement this separately)
        place_order(symbol, action, timeframe)

        logging.info(f"Order placed for {symbol} to {action} of timeframe:{timeframe}M.")
        return jsonify({"status": "success"}), 200

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(port=5000, debug=True)
