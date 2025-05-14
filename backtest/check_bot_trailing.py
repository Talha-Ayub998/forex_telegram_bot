import pandas as pd
from datetime import datetime

# Load signals and price data
signals_df = pd.read_csv("signals.csv")
price_df = pd.read_csv("XAUUSD_M5_from_2023.csv", parse_dates=["datetime"])

# Convert and sort timestamps
signals_df["datetime"] = pd.to_datetime(signals_df["Date"] + " " + signals_df["Time"])
signals_df = signals_df.sort_values("datetime").reset_index(drop=True)
price_df = price_df.sort_values("datetime").reset_index(drop=True)

# Filter for May 2025 only
signals_df = signals_df[(signals_df["datetime"] >= "2025-05-01") & (signals_df["datetime"] < "2025-06-01")]
price_df = price_df[(price_df["datetime"] >= "2025-05-01") & (price_df["datetime"] < "2025-06-01")]

# Backtest config
starting_balance = 10000
current_balance = starting_balance
cumulative_loss = 0
contract_size = 100
results = []

# Strategy parameters
initial_sl_offset = 3
sl_move_trigger = 2
sl_after_move = 1
profit_target_pct = 0.01

# Simulate trades
for _, signal in signals_df.iterrows():
    entry_time = signal["datetime"]
    entry_price = signal["Price"]
    signal_type = signal["Signal"].upper()
    low = signal["Low"]
    high = signal["High"]

    lot_size = 0.2
    sl_moved = False
    sl_type = "Initial"
    initial_sl = None
    current_price = None
    profit_formula = ""

    # Set SL based on signal
    if signal_type == "BUY":
        sl = low - initial_sl_offset
        initial_sl = sl
    elif signal_type == "SELL":
        sl = high + initial_sl_offset
        initial_sl = sl
    else:
        continue

    future_candles = price_df[price_df["datetime"] > entry_time].copy()
    outcome = None
    exit_time = None
    profit = 0

    for _, candle in future_candles.iterrows():
        current_price = candle["Close"]

        if signal_type == "BUY":
            if not sl_moved and current_price >= entry_price + sl_move_trigger:
                sl = entry_price + sl_after_move
                sl_moved = True
                sl_type = "Moved"

            # SL Hit
            if current_price <= sl:
                exit_price = sl
                profit = (exit_price - entry_price) * lot_size * contract_size
                profit_formula = f"({exit_price} - {entry_price}) * {lot_size} * {contract_size}"
                current_balance += profit
                exit_time = candle["datetime"]

                if profit < 0:
                    cumulative_loss += abs(profit)
                    outcome = "LOSS"
                elif profit > 0:
                    cumulative_loss = 0
                    outcome = "WIN"
                else:
                    outcome = "BREAKEVEN"
                break

            # TP (floating profit) Hit
            floating_profit = (current_price - entry_price) * lot_size * contract_size
            if floating_profit >= current_balance * profit_target_pct:
                profit = floating_profit
                profit_formula = f"({current_price} - {entry_price}) * {lot_size} * {contract_size}"
                current_balance += profit
                cumulative_loss = 0
                outcome = "WIN"
                exit_time = candle["datetime"]
                break

        elif signal_type == "SELL":
            if not sl_moved and current_price <= entry_price - sl_move_trigger:
                sl = entry_price - sl_after_move
                sl_moved = True
                sl_type = "Moved"

            # SL Hit
            if current_price >= sl:
                exit_price = sl
                profit = (entry_price - exit_price) * lot_size * contract_size
                profit_formula = f"({entry_price} - {exit_price}) * {lot_size} * {contract_size}"
                current_balance += profit
                exit_time = candle["datetime"]

                if profit < 0:
                    cumulative_loss += abs(profit)
                    outcome = "LOSS"
                elif profit > 0:
                    cumulative_loss = 0
                    outcome = "WIN"
                else:
                    outcome = "BREAKEVEN"
                break

            # TP (floating profit) Hit
            floating_profit = (entry_price - current_price) * lot_size * contract_size
            if floating_profit >= current_balance * profit_target_pct:
                profit = floating_profit
                profit_formula = f"({entry_price} - {current_price}) * {lot_size} * {contract_size}"
                current_balance += profit
                cumulative_loss = 0
                outcome = "WIN"
                exit_time = candle["datetime"]
                break

    if outcome in ["WIN", "LOSS", "BREAKEVEN"]:
        results.append({
            "Entry Time": entry_time,
            "Signal": signal_type,
            "Entry Price": entry_price,
            "Current Price": round(current_price, 2),
            "Lot Size": round(lot_size, 4),
            "Initial SL": round(initial_sl, 2),
            "Final SL": round(sl, 2),
            "SL Moved": sl_moved,
            "SL Type": sl_type,
            "Exit Time": exit_time,
            "Outcome": outcome,
            "Profit Formula": profit_formula,
            "Profit": round(profit, 2),
            "Cumulative Loss": round(cumulative_loss, 2),
            "Balance After Trade": round(current_balance, 2)
        })

# Save to CSV
results_df = pd.DataFrame(results)
results_df.to_csv("backtest_final_strategy.csv", index=False)

print("✅ Backtest complete with detailed debug fields saved to 'backtest_final_strategy.csv'")
