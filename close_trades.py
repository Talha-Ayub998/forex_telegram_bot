import MetaTrader5 as mt5


def initialize_meta_trader(path, login, password, servername):
    try:
        if not mt5.initialize(path=path, login=login, password=password, server=servername):
            print(f"initialize() failed, error code = {mt5.last_error()}")
            return False
    except:
        print('Check Metatrader Credentials i.e. Login,Password,Server')

def close_all_trades():
    try:
        # Get all open positions
        positions = mt5.positions_get()
        if positions is None:
            print(f"No positions to close. Error: {mt5.last_error()}")
            return

        # Iterate over each position and close it
        for position in positions:
            symbol = position.symbol
            volume = position.volume
            ticket = position.ticket
            order_type = mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY

            # Get the current price for the symbol
            price = mt5.symbol_info_tick(symbol).bid if order_type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(symbol).ask

            # Create a close request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": order_type,
                "position": ticket,
                "price": price,
                "magic": 999,  # Same magic number used for identifying trades
                "comment": "Close All Trades",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            # Send the trade request
            result = mt5.order_send(request)
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"Successfully closed position {ticket} for {symbol} with volume {volume}.")
            else:
                print(f"Failed to close position {ticket} for {symbol}. Error: {result.comment}")

    except Exception as e:
        print(f"Error while closing trades: {e}")


# LOGIN = 241273863
# SERVER = 'Exness-MT5Trial'
# PASSWORD = 'Panda_22'
# PATH = 'C:\\Program Files\\MetaTrader 5 EXNESS\\terminal64.exe'


# LOGIN = 52114068
# SERVER = 'ICMarketsSC-Demo'
# PASSWORD = 'ska6kwS&k&$dnQ'
# PATH = 'C:\\Program Files\\MetaTrader 5 IC Markets Global\\terminal64.exe'


LOGIN = 61303556
SERVER = 'Pepperstone-Demo'
PASSWORD = 'cTCXW#3T3pz2@bj'
PATH = 'C:\\Program Files\\Pepperstone MetaTrader 5\\terminal64.exe'

if __name__ == "__main__":
    initialize_meta_trader(PATH, int(LOGIN), PASSWORD, SERVER)
    close_all_trades()

    mt5.shutdown()