from telethon import TelegramClient, events
import asyncio
import MetaTrader5 as mt5
from datetime import datetime, timezone
import re
import os
import json

print("Code is Ready")


def initialize_meta_trader(path, login, password, servername):
    try:
        if not mt5.initialize(path=path, login=login, password=password, server=servername):
            print(f"initialize() failed, error code = {mt5.last_error()}")
            return False
    except:
        print('Check Metatrader Credentials i.e. Login,Password,Server')


def open_order(order_type, symbol, volume, entry_price, tp, sl):
    """
    Opens a market order (Buy/Sell) with the specified parameters.
    """
    try:
        # Validate order type
        if order_type not in ['Buy', 'Sell']:
            raise ValueError("Invalid order_type. Use 'Buy' or 'Sell'.")
        # Determine order-specific parameters
        order_type_mapping = {
            'Buy': {
                'type': mt5.ORDER_TYPE_BUY,
                'price': mt5.symbol_info_tick(symbol).ask
            },
            'Sell': {
                'type': mt5.ORDER_TYPE_SELL,
                'price': mt5.symbol_info_tick(symbol).bid
            }
        }
        order_details = order_type_mapping[order_type]
        # Create the trade request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(volume),
            "type": order_details['type'],
            "price": order_details['price'],
            "tp": float(tp),
            "sl": float(sl),
            "magic": 999,
            "comment": "Bot",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        # Send the trade request
        result = mt5.order_send(request)
        # Check the result
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"Order Opened: Order ID {result.order} | {order_type} {symbol} | Volume: {
                  volume} | Entry Price: {order_details['price']} | TP: {tp} | SL: {sl}")
            return result.order
        else:
            print(f"Trade failed: {result.comment}")
            return None
    except Exception as e:
        print(f"Error opening order: {e}")


# def update_order(order_id, sl=None, tp=None):
#     try:
#         # Get the existing order details
#         order_info = mt5.history_orders_get(
#             ticket=order_id) or mt5.positions_get(ticket=order_id)

#         if not order_info:
#             print(f"Order with ID {order_id} not found.")
#             return False

#         # Extract relevant details for modification

#         order_info = order_info[0] if isinstance(
#             order_info, tuple) else order_info
#         symbol = order_info.symbol
#         volume = order_info.volume_initial

#         # Prepare the modification request
#         request = {
#             "action": mt5.TRADE_ACTION_SLTP,  # Modify SL and TP
#             "symbol": symbol,
#             "volume": float(volume),
#             "position": order_id,  # Order ID to modify
#             "sl": float(sl) if sl else order_info.sl,
#             "tp": float(tp) if tp else order_info.tp,
#         }

#         # Send the modification request
#         result = mt5.order_send(request)

#         # Check the result
#         if result.retcode == mt5.TRADE_RETCODE_DONE:
#             print(f"Order ID {order_id} updated: SL={
#                   request['sl']}, TP={request['tp']}")
#             return True
#         else:
#             print(f"Failed to update order ID {order_id}: {result.comment}")
#             return False

#     except Exception as e:
#         print(f"Error updating order ID {order_id}: {e}")
#         return False


# def save_order_to_json(order_id, order_details):
#     file_name = "orders.json"

#     # Check if the JSON file exists
#     if os.path.exists(file_name):
#         try:
#             # Load existing data
#             with open(file_name, "r") as file:
#                 data = json.load(file)
#         except json.JSONDecodeError:
#             # Handle case where file exists but is empty or invalid
#             print(f"{file_name} is empty or invalid. Initializing as empty list.")
#             data = []
#     else:
#         data = []

#     # Check if the order_id already exists
#     if any(order.get("order_id") == order_id for order in data):
#         print(f"Order ID {order_id} already exists. Skipping save.")
#         return

#     # Add the new order details
#     data.append({
#         "order_id": order_id,
#         **order_details
#     })

#     # Write the updated data back to the JSON file
#     with open(file_name, "w") as file:
#         json.dump(data, file, indent=4)
#     print(f"Order ID {order_id} saved successfully.")


# def process_order_with_single_message(symbol, order_type, volume):

#     price = mt5.symbol_info_tick(
#         symbol).bid if order_type == "Sell" else mt5.symbol_info_tick(symbol).ask

#     sl = price - 6 if order_type == "Buy" else price + 6

#     tp = price + 2 if order_type == "Buy" else price - 2

#     # Place the first order
#     order_id1 = open_order(order_type=order_type, symbol=symbol,
#                            volume=volume, entry_price=price, tp=tp, sl=sl)
#     if order_id1:
#         save_order_to_json(
#             order_id=order_id1,
#             order_details={
#                 "symbol": symbol,
#                 "order_type": order_type,
#                 "price": price,
#                 "sl": sl,
#                 "tp": tp
#             }
#         )

#     # Place the second order
#     order_id2 = open_order(order_type=order_type, symbol=symbol,
#                            volume=volume, entry_price=price, tp=tp, sl=sl)
#     if order_id2:
#         save_order_to_json(
#             order_id=order_id2,
#             order_details={
#                 "symbol": symbol,
#                 "order_type": order_type,
#                 "price": price,
#                 "sl": sl,
#                 "tp": tp
#             }
#         )

#     print(f"Trade executed: {order_type} {
#           symbol} @ {price}, SL: {sl}, TP: {tp}")


# def process_order_with_box_message(message, symbol, order_type, volume=0.1):
#     file_name = "orders.json"

#     # Load existing orders from the JSON file
#     if os.path.exists(file_name):
#         try:
#             with open(file_name, "r") as file:
#                 orders = json.load(file)
#         except json.JSONDecodeError:
#             orders = []
#     else:
#         orders = []


#     # price_high_match = re.search(r"buy now\s*([\d.]+)", message, re.IGNORECASE)
#     # price_high = float(price_high_match.group(1)) if price_high_match else None

#     # # Extract low price
#     # price_low_match = re.search(r"-\s*([\d.]+)", message, re.IGNORECASE)
#     # price_low = float(price_low_match.group(1)) if price_low_match else None

#     price = mt5.symbol_info_tick(
#         symbol).bid if order_type == "Sell" else mt5.symbol_info_tick(symbol).ask

#     # Extract SL
#     sl_match = re.search(r"SL\s*:\s*([\d.]+)", message, re.IGNORECASE)
#     sl = float(sl_match.group(1)) if sl_match else None

#     # Extract each TP into separate variables
#     tp_matches = re.findall(r"TP\s*:\s*([\d.]+|open)", message, re.IGNORECASE)
#     tp1 = float(tp_matches[0])
#     tp2 = float(tp_matches[1])
#     # tp3 = float(tp_matches[2]) if len(
#     #     tp_matches) > 2 and tp_matches[2].lower() != "open" else "open"
#     # tp4 = tp_matches[3] if len(tp_matches) > 3 else None  # "open" remains a string
#     print("Data in the orders (in-memory):", orders)

#     # Check if there are existing orders
#     if orders:
#         # Iterate over the orders in pairs
#         for i in range(0, len(orders), 2):
#             if i + 1 < len(orders):  # Ensure there is a second order in the pair
#                 # Update the first order in the pair with TP1
#                 update_order(orders[i]['order_id'], sl=sl, tp=tp1)
#                 print(f"Updated Order ID {
#                       orders[i]['order_id']}: SL={sl}, TP={tp1}")

#                 # Update the second order in the pair with TP2
#                 update_order(orders[i+1]['order_id'], sl=sl, tp=tp2)
#                 print(f"Updated Order ID {
#                       orders[i + 1]['order_id']}: SL={sl}, TP={tp2}")
#             else:
#                 print(f"Error: Unmatched order at index {i}.")
#             # Clear the JSON file after processing existing orders
#         with open(file_name, "w") as file:
#             file.write("[]")
#         print("Cleared all orders from the JSON file.")
#     else:
#         # Create new orders only if all parameters are present
#         if price and sl and tp1 and tp2:
#             print("No existing orders. Creating new orders without saving.")
#             # Create the first order with TP1
#             open_order(order_type, symbol, volume, price, tp1, sl)
#             # Create the second order with TP2
#             open_order(order_type, symbol, volume, price, tp2, sl)
#         else:
#             print("Missing necessary parameters (price, SL, TP1, TP2) to create orders.")

def process_order_with_single_message(symbol, order_type, volume):

    price = mt5.symbol_info_tick(symbol).bid if order_type == "Sell" else mt5.symbol_info_tick(symbol).ask

    sl = price - 6 if order_type == "Buy" else price + 6

    if order_type == "Buy":
        sl = price - 6  # SL for Buy
        tp1 = price + 2  # TP1 for Buy
        tp2 = price + 4  # TP2 for Buy
    else:  # For Sell orders
        sl = price + 6  # SL for Sell
        tp1 = price - 2  # TP1 for Sell
        tp2 = price - 4  # TP2 for Sell

        # Place the first order with TP1
    open_order(order_type=order_type, symbol=symbol,
               volume=volume, entry_price=price, tp=tp1, sl=sl)

    # Place the second order with TP2
    open_order(order_type=order_type, symbol=symbol,
               volume=volume, entry_price=price, tp=tp2, sl=sl)

    print(f"Trade executed: {order_type} {symbol} @ {price}, SL: {sl}, TP1: {tp1}, TP2: {tp2}")

api_id = '22871764'
api_hash = '533041c6ece060f46924c19adf6df394'
group_username = "gtmointernational"  # The group username
# group_username = "testingnewbitpro"  # The group username
chat_id = -1001841516484
chat_id = None
client = TelegramClient("session_name", api_id, api_hash)
output_file = "messages.txt"


# LOGIN = 52114068
# SERVER = 'ICMarketsSC-Demo'
# PASSWORD = 'ska6kwS&k&$dnQ'
# PATH = 'C:\\Program Files\\MetaTrader 5 IC Markets Global\\terminal64.exe'

LOGIN = 61303556
SERVER = 'Pepperstone-Demo'
PASSWORD = 'cTCXW#3T3pz2@bj'
PATH = 'C:\\Program Files\\Pepperstone MetaTrader 5\\terminal64.exe'




initialize_meta_trader(PATH, int(LOGIN), PASSWORD, SERVER)

# Asynchronous function to listen for messages


async def main():
    await client.start()
    print("Bot is running and listening for messages...")
    # Event listener for new messages in the group

    @client.on(events.NewMessage(chats=chat_id or group_username))
    async def handler(event):
        # Get message text
        message = event.message.message
        # Check if the message contains "XAUUSD SELL" or "XAUUSD BUY"
        message = message.lower()
        symbol = 'XAUUSD'
        if "gold sell now" in message or "gold buy now" in message:
            # Determine order type
            order_type = "Sell" if "sell" in message else "Buy"

            # Single msg with two trades
            if "open" not in message:  # Check if additional details are missing
                process_order_with_single_message(
                    symbol=symbol, order_type=order_type, volume=0.1)

            # elif "open" in message:
            #     process_order_with_box_message(message, symbol, order_type)

        else:
            # Exit if no relevant message
            return

        # Get the current UTC timestamp
        timestamp = datetime.now(timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S %Z")
        # Format the message with the UTC timestamp
        formatted_message = f"{timestamp} - {message}"
        print(f"Filtered message received: {formatted_message}")
        # Save the filtered message to the file
        with open(output_file, "a", encoding="utf-8") as file:
            file.write(formatted_message + "\n")
    # Keep the client running
    await client.run_until_disconnected()

# Run the client
asyncio.run(main())
