from flask import Flask, request, jsonify
import logging
import json
import MetaTrader5 as mt5
import os

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

def save_mapping(current_order_id, pending_order_id, symbol, action, timeframe, entry_price, pending_entry_price, pending_order_type):
    try:
        # File name based on the symbol
        file_name = f"{symbol}_order_mapping.json"

        # Create a mapping dictionary
        mapping = {
            "current_order_id": current_order_id,
            "pending_order_id": pending_order_id,
            "symbol": symbol,
            "current_action": action,
            "pending_action": pending_order_type,
            "timeframe": timeframe,
            "current_entry_price": entry_price,
            "pending_entry_price": pending_entry_price
        }

        # Check if the file exists
        if os.path.exists(file_name):
            try:
                # Load existing data from the file
                with open(file_name, "r") as file:
                    data = json.load(file)  # Load JSON as a list
            except json.JSONDecodeError:
                # If the file is empty or corrupted, start with an empty list
                data = []
        else:
            # If the file doesn't exist, start with an empty list
            data = []

        # Append the new mapping to the list
        data.append(mapping)

        # Save the updated list back to the file
        with open(file_name, "w") as file:
            json.dump(data, file, indent=4)  # Pretty-print with indentation

        print(f"Order mapping saved: {mapping}")
    except Exception as e:
        print(f"Error saving order mapping: {e}")


def place_order_with_pending(symbol, action, timeframe, low_price):
    try:
        entry_price = mt5.symbol_info_tick(symbol).ask if action == "buy" else mt5.symbol_info_tick(symbol).bid
        # Determine current order details
        if action == "buy":
            current_order_type = mt5.ORDER_TYPE_BUY
            sl = low_price - 1
            tp = entry_price + (29 if timeframe in [10, 15] else 24 if timeframe == 5 else 19)
        elif action == "sell":
            current_order_type = mt5.ORDER_TYPE_SELL
            sl = low_price + 1
            tp = entry_price - (29 if timeframe in [10, 15] else 24 if timeframe == 5 else 19)
        else:
            print("Invalid order type")
            return

        # Place current market order
        lot_size = 0.1
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
        print("Placing current market order:", request)
        result = mt5.order_send(request)

        if result.retcode == mt5.TRADE_RETCODE_DONE:
            current_order_id = result.order
            print(f"Current order successfully placed: {current_order_id}")

            # Define details for pending order
            if action == "buy":
                pending_order_type = mt5.ORDER_TYPE_SELL_STOP
                pending_entry_price = sl  # SL of current buy is entry for pending sell
                pending_sl = pending_entry_price + 10
                pending_tp = pending_entry_price - (29 if timeframe in [10, 15] else 24 if timeframe == 5 else 19)
            elif action == "sell":
                pending_order_type = mt5.ORDER_TYPE_BUY_STOP
                pending_entry_price = sl  # SL of current sell is entry for pending buy
                pending_sl = pending_entry_price - 10
                pending_tp = pending_entry_price + (29 if timeframe in [10, 15] else 24 if timeframe == 5 else 19)

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
            print("Placing pending order:", pending_request)
            pending_result = mt5.order_send(pending_request)

            if pending_result.retcode == mt5.TRADE_RETCODE_DONE:
                pending_order_id = pending_result.order
                print(f"Pending order successfully placed: {pending_order_id}")

                # Save mapping between current order and pending order
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
                print(f"Failed to place pending order: {pending_result.retcode}")
        else:
            print(f"Failed to place current order: {result.retcode}")
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
        timeframe = int(data.get('time_frame'))
        low_price = float(data.get('price'))

        # Call place_order function (implement this separately)
        place_order_with_pending(symbol, action, timeframe, low_price)

        logging.info(f"Order placed for {symbol} to {action} of timeframe:{timeframe}M.")
        return jsonify({"status": "success"}), 200

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(port=5000, debug=True)
