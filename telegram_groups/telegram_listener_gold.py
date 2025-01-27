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
        try:
            # Get message text
            if not event.message or not event.message.message:
                print("Non-text message received, ignoring...")
                return

            message = event.message.message.lower()
            symbol = 'XAUUSD'

            # Check if the message contains "gold sell now" or "gold buy now"
            if "gold sell now" in message or "gold buy now" in message:
                # Determine order type
                order_type = "Sell" if "sell" in message else "Buy"

                # Single msg with two trades
                if "open" not in message:  # Check if additional details are missing
                    process_order_with_single_message(
                        symbol=symbol, order_type=order_type, volume=0.1
                    )

            # Log and format the message with the UTC timestamp
            timestamp = datetime.now(timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S %Z"
            )
            formatted_message = f"{timestamp} - {message}"
            print(f"Filtered message received: {formatted_message}")

            # Save the filtered message to the file
            with open(output_file, "a", encoding="utf-8") as file:
                file.write(formatted_message + "\n")

        except Exception as e:
            print(f"Error in message handler: {e}")

    # Keep the client running
    await client.run_until_disconnected()

# Run the client
asyncio.run(main())
