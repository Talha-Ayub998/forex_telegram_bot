import json
import MetaTrader5 as mt5
import pandas as pd
import pandas_ta as ta
import time


def initialize_meta_trader(path, login, password, servername):
    try:
        if not mt5.initialize(path=path, login=login, password=password, server=servername):
            print(f"initialize() failed, error code = {mt5.last_error()}")
            return False
    except:
        print('Check Metatrader Credentials i.e. Login,Password,Server')


# Fetch data and calculate RSI for all timeframes
def fetch_and_calculate_rsi(symbol, timeframe, rsi_period, drop_latest=True):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 500)  # Fetch 500 candles
    if rates is None:
        print(f"Failed to fetch data for {symbol} in timeframe {timeframe}")
        return None

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)

    # Optionally drop the latest row (incomplete candle)
    if drop_latest:
        df = df[:-1]

    # Calculate RSI using pandas-ta
    df['rsi'] = ta.rsi(df['close'], length=rsi_period)
    return df

# Check conditions and place orders


def check_and_trade(symbol, df, overbought, oversold, min_duration, timeframe):
    # Ensure the DataFrame and RSI column are valid
    if df is None or 'rsi' not in df.columns:
        print(f"Data unavailable or RSI not calculated for {symbol}. Skipping.")
        return

    # Ensure there are enough rows for calculations (at least 3 for [-2] and [-3])
    if len(df) < 3:
        print(f"Insufficient data for trading logic for {symbol}. Skipping.")
        return

    # Calculate slope and duration conditions
    df['rsi_slope'] = df['rsi'].diff()
    df['overbought_duration'] = df['rsi'].rolling(window=min_duration).apply(
        lambda x: sum(x > overbought), raw=False
    )
    df['oversold_duration'] = df['rsi'].rolling(window=min_duration).apply(
        lambda x: sum(x < oversold), raw=False
    )

    # Check if required columns exist
    required_columns = ['rsi', 'rsi_slope', 'overbought_duration', 'oversold_duration']
    if not all(col in df.columns for col in required_columns):
        print(f"Missing required columns in DataFrame for {symbol}. Skipping.")
        return

    # Get the latest completed bar (-2) and previous bar (-3)
    latest = df.iloc[-2]

    # Check signals based on RSI and duration conditions
    if latest['rsi'] < oversold and latest['rsi_slope'] > 0 and latest['oversold_duration'] >= min_duration:
        print(f"Buy signal detected on {timeframe} timeframe. Placing order...")
        place_order(symbol, action="buy", timeframe=timeframe)  # Pass timeframe
    elif latest['rsi'] > overbought and latest['rsi_slope'] < 0 and latest['overbought_duration'] >= min_duration:
        print(f"Sell signal detected on {timeframe} timeframe. Placing order...")
        place_order(symbol, action="sell", timeframe=timeframe)  # Pass timeframe



# Place order
def place_order(symbol, action, timeframe):
    if action == "buy":
        order_type = mt5.ORDER_TYPE_BUY
    elif action == "sell":
        order_type = mt5.ORDER_TYPE_SELL
    else:
        print("Invalid order type")
        return

    lot_size = 0.1  # Adjust lot size as needed
    price = mt5.symbol_info_tick(
        symbol).ask if action == "buy" else mt5.symbol_info_tick(symbol).bid
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
    result = mt5.order_send(request)

    # Log order details if successful
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        order_details = {
            "order_id": result.order,
            "symbol": symbol,
            "action": action,
            "timeframe": timeframe,  # Include timeframe
            "volume": lot_size,
            "price": price,
            "comment": f"RSI Signal-{timeframe}",
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        print(f"Order Opened: {order_details}")
        log_order_to_file(order_details, file_name=f"{symbol}_orders_log.json")
    else:
        print(f"Failed to place order: {result.retcode}")
        # Optionally log failed attempts
        failed_order_details = {
            "symbol": symbol,
            "action": action,
            "timeframe": timeframe,  # Include timeframe
            "volume": lot_size,
            "price": price,
            "comment": f"RSI Signal-{timeframe}",
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "error": result.retcode,
        }
        log_order_to_file(failed_order_details, f"{symbol}_failed_orders_log.json")  # Log failed orders

# Function to save order details to a JSON file

def log_order_to_file(order_details, file_name):
    try:
        # Load existing log file or create a new one
        try:
            with open(file_name, "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            data = []  # If file doesn't exist, start with an empty list

        # Append the new order details
        data.append(order_details)

        # Save back to the file
        with open(file_name, "w") as f:
            json.dump(data, f, indent=4)
        print(f"Order logged successfully: {order_details}")
    except Exception as e:
        print(f"Failed to log order: {e}")


# Parameters
symbol = "XAUUSDm"
# symbol = "BTCUSDm"
timeframes = {
    "1m": mt5.TIMEFRAME_M1,
    "3m": mt5.TIMEFRAME_M3,
    "5m": mt5.TIMEFRAME_M5,
    "10m": mt5.TIMEFRAME_M10,
    "15m": mt5.TIMEFRAME_M15,
}
rsi_period = 14
overbought = 70
oversold = 30
min_duration = 4  # Minimum candles in overbought/oversold zone

LOGIN = 241273863
SERVER = 'Exness-MT5Trial'
PASSWORD = 'Panda_22'
PATH = 'C:\\Program Files\\MetaTrader 5 EXNESS\\terminal64.exe'
initialize_meta_trader(PATH, int(LOGIN), PASSWORD, SERVER)


# Main loop
while True:
    for label, tf in timeframes.items():
        print(f"Checking timeframe {label} for {symbol}...")
        df = fetch_and_calculate_rsi(symbol, tf, rsi_period)
        # print(f"Dataframe of Label:{label} \n\n {df}")
        check_and_trade(symbol, df, overbought, oversold, min_duration, tf)
    time.sleep(60)  # Run every second
