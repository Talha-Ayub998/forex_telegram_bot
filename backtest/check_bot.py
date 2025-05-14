### Convert xls to csv ###

# import pandas as pd

# # Load Excel file (adjust extension as needed: .xls, .xlsx, .xlsm)
# df = pd.read_excel("XAUUSD_M5_from_2020.xlsx", engine="openpyxl")

# # Save to CSV
# df.to_csv("XAUUSD_M5_from_2020.csv", index=False)



import pandas as pd
from datetime import datetime

# Load data
signals_df = pd.read_csv("signals.csv")
price_df = pd.read_csv("XAUUSD_M5_from_2023.csv", parse_dates=["datetime"])

# Convert signal datetime
signals_df["datetime"] = pd.to_datetime(signals_df["Date"] + " " + signals_df["Time"])

# Sort and filter both datasets for May 2025
signals_df = signals_df.sort_values("datetime").reset_index(drop=True)
price_df = price_df.sort_values("datetime").reset_index(drop=True)

# Filter for May 2025 only
signals_df = signals_df[(signals_df["datetime"] >= "2025-05-01") & (signals_df["datetime"] < "2025-06-01")]
price_df = price_df[(price_df["datetime"] >= "2025-05-01") & (price_df["datetime"] < "2025-06-01")]

# Backtest settings
starting_balance = 10000
current_balance = starting_balance
cumulative_loss = 0
results = []

# Run backtest
for _, signal in signals_df.iterrows():
    entry_time = signal["datetime"]
    entry_price = signal["Price"]
    signal_type = signal["Signal"].upper()

    # Dynamic TP calculation (with min $1)
    required_profit = max(cumulative_loss + (current_balance * 0.01), 1.0)

    # Set SL and TP based on signal direction
    if signal_type == "BUY":
        sl = signal["Low"] - 3.0
        tp = entry_price + required_profit
    elif signal_type == "SELL":
        sl = signal["High"] + 3.0
        tp = entry_price - required_profit
    else:
        continue  # Skip unknown signals

    # Get price candles after entry
    future_candles = price_df[price_df["datetime"] > entry_time].copy()

    # Initialize trade outcome
    outcome = None
    exit_time = None
    profit = 0

    for _, candle in future_candles.iterrows():
        if signal_type == "BUY":
            if candle["Low"] <= sl:
                loss = entry_price - sl
                current_balance -= loss
                cumulative_loss += loss
                profit = -loss
                outcome = "LOSS"
                exit_time = candle["datetime"]
                break
            if candle["High"] >= tp:
                gain = tp - entry_price
                if gain <= 0:
                    outcome = "BREAKEVEN"
                    profit = 0
                else:
                    current_balance += gain
                    cumulative_loss = 0
                    profit = gain
                    outcome = "WIN"
                exit_time = candle["datetime"]
                break

        elif signal_type == "SELL":
            if candle["High"] >= sl:
                loss = sl - entry_price
                current_balance -= loss
                cumulative_loss += loss
                profit = -loss
                outcome = "LOSS"
                exit_time = candle["datetime"]
                break
            if candle["Low"] <= tp:
                gain = entry_price - tp
                if gain <= 0:
                    outcome = "BREAKEVEN"
                    profit = 0
                else:
                    current_balance += gain
                    cumulative_loss = 0
                    profit = gain
                    outcome = "WIN"
                exit_time = candle["datetime"]
                break

    if outcome in ["WIN", "LOSS"]:
        results.append({
            "Entry Time": entry_time,
            "Signal": signal_type,
            "Entry Price": entry_price,
            "SL": round(sl, 2),
            "TP": round(tp, 2),
            "Exit Time": exit_time,
            "Outcome": outcome,
            "Profit": round(profit, 2),
            "Balance After Trade": round(current_balance, 2)
        })

# Create a DataFrame for results
results_df = pd.DataFrame(results)

# Save to CSV
results_df.to_csv("backtest_may2025_results.csv", index=False)
print("✅ Backtest complete for May 2025. Results saved to 'backtest_may2025_results.csv'")











####################

import pandas as pd
from datetime import datetime

# Load data
signals_df = pd.read_csv("signals.csv")
price_df = pd.read_csv("XAUUSD_M5_from_2023.csv", parse_dates=["datetime"])

# Convert signal datetime
signals_df["datetime"] = pd.to_datetime(signals_df["Date"] + " " + signals_df["Time"])

# Sort and filter both datasets for May 2025
signals_df = signals_df.sort_values("datetime").reset_index(drop=True)
price_df = price_df.sort_values("datetime").reset_index(drop=True)

# Filter for May 2025 only (comment out for full run)
# signals_df = signals_df[(signals_df["datetime"] >= "2025-05-01") & (signals_df["datetime"] < "2025-06-01")]
# price_df = price_df[(price_df["datetime"] >= "2025-05-01") & (price_df["datetime"] < "2025-06-01")]

# Backtest settings
starting_balance = 10000
current_balance = starting_balance
cumulative_loss = 0
contract_size = 100  # 1 lot = 100 ounces of gold
results = []

# Run backtest
for _, signal in signals_df.iterrows():
    entry_time = signal["datetime"]
    entry_price = signal["Price"]
    signal_type = signal["Signal"].upper()

    # Dynamically scale lot size so 10k balance → 0.2 lots
    lot_size = current_balance / 50000  # (10,000 → 0.2 lot)
    # lot_size = current_balance / 100000  # (10,000 → 0.1 lot)

    # Calculate required profit in $ and translate to price move
    required_profit_usd = max(cumulative_loss + (current_balance * 0.01), 1.0)
    required_price_move = required_profit_usd / (lot_size * contract_size)
    tp = 3
    sl = 5

    # Set SL and TP based on signal direction
    if signal_type == "BUY":
        sl = signal["Low"] - sl
        tp = entry_price + tp
    elif signal_type == "SELL":
        sl = signal["High"] + sl
        tp = entry_price - tp
    else:
        continue  # Skip unknown signals

    # Get price candles after entry
    future_candles = price_df[price_df["datetime"] > entry_time].copy()

    # Initialize trade outcome
    outcome = None
    exit_time = None
    profit = 0

    for _, candle in future_candles.iterrows():
        if signal_type == "BUY":
            if candle["Low"] <= sl:
                loss = (entry_price - sl) * lot_size * contract_size
                current_balance -= loss
                cumulative_loss += loss
                profit = -loss
                outcome = "LOSS"
                exit_time = candle["datetime"]
                break
            if candle["High"] >= tp:
                gain = (tp - entry_price) * lot_size * contract_size
                if gain <= 0:
                    outcome = "BREAKEVEN"
                    profit = 0
                else:
                    current_balance += gain
                    cumulative_loss = 0
                    profit = gain
                    outcome = "WIN"
                exit_time = candle["datetime"]
                break

        elif signal_type == "SELL":
            if candle["High"] >= sl:
                loss = (sl - entry_price) * lot_size * contract_size
                current_balance -= loss
                cumulative_loss += loss
                profit = -loss
                outcome = "LOSS"
                exit_time = candle["datetime"]
                break
            if candle["Low"] <= tp:
                gain = (entry_price - tp) * lot_size * contract_size
                if gain <= 0:
                    outcome = "BREAKEVEN"
                    profit = 0
                else:
                    current_balance += gain
                    cumulative_loss = 0
                    profit = gain
                    outcome = "WIN"
                exit_time = candle["datetime"]
                break

    if outcome in ["WIN", "LOSS"]:
        results.append({
            "Entry Time": entry_time,
            "Signal": signal_type,
            "Entry Price": entry_price,
            "Lot Size": round(lot_size, 4),
            "SL": round(sl, 2),
            "TP": round(tp, 2),
            "Exit Time": exit_time,
            "Outcome": outcome,
            "Profit": round(profit, 2),
            "Balance After Trade": round(current_balance, 2)
        })

# Create a DataFrame for results
results_df = pd.DataFrame(results)

# Save to CSV
results_df.to_csv("backtest_final_results_by.csv", index=False)
print("✅ Backtest complete for May 2025. Results saved to 'backtest_may2025_results.csv'")
