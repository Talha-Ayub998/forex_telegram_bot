import pandas as pd
from datetime import datetime

# Load signals and price data
signals_df = pd.read_csv("signals.csv")
price_df = pd.read_csv("XAUUSD_M5_from_2023.csv", parse_dates=["datetime"])


# Convert and sort timestamps
signals_df["datetime"] = pd.to_datetime(signals_df["Date"] + " " + signals_df["Time"])
signals_df = signals_df.sort_values("datetime").reset_index(drop=True)
price_df = price_df.sort_values("datetime").reset_index(drop=True)

signals_df = signals_df[(signals_df["datetime"] >= "2025-05-01") & (signals_df["datetime"] < "2025-06-01")]
price_df = price_df[(price_df["datetime"] >= "2025-05-01") & (price_df["datetime"] < "2025-06-01")]


# Backtest configuration
starting_balance = 10000
current_balance = starting_balance
cumulative_loss = 0
contract_size = 100
results = []

# Strategy parameters (in actual price units)
initial_sl_offset = 4          # SL is 400 points below entry
sl_move_trigger = 4            # Price must move +400 to adjust SL
sl_after_move = 1              # New SL = entry + 100
profit_target_pct = 0.01         # Target 1% floating profit

# Begin trade-by-trade simulation
for _, signal in signals_df.iterrows():
    entry_time = signal["datetime"]
    entry_price = signal["Price"]
    signal_type = signal["Signal"].upper()

    lot_size = 0.2  # 10k balance = 0.2 lots
    sl_moved = False

    # Set initial SL based on signal type
    if signal_type == "BUY":
        sl = entry_price - initial_sl_offset
    elif signal_type == "SELL":
        sl = entry_price + initial_sl_offset
    else:
        continue

    future_candles = price_df[price_df["datetime"] > entry_time].copy()
    outcome = None
    exit_time = None
    profit = 0

    # Evaluate each candle after entry
    for _, candle in future_candles.iterrows():
        current_price = candle["Close"]

        if signal_type == "BUY":
            # Step 1: Move SL once if price reaches (entry + 400)
            if not sl_moved and current_price >= entry_price + sl_move_trigger:
                sl = entry_price + sl_after_move  # e.g., 1000 + 100 = 1100
                sl_moved = True

            # Step 2: Exit if current price <= SL
            if current_price <= sl:
                loss = abs(entry_price - sl) * lot_size * contract_size
                current_balance -= loss
                cumulative_loss += loss
                profit = -loss
                outcome = "LOSS"
                exit_time = candle["datetime"]
                break

            # Step 3: Exit if floating profit hits 1%
            floating_profit = (current_price - entry_price) * lot_size * contract_size
            if floating_profit >= current_balance * profit_target_pct:
                current_balance += floating_profit
                cumulative_loss = 0
                profit = floating_profit
                outcome = "WIN"
                exit_time = candle["datetime"]
                break

        elif signal_type == "SELL":
            if not sl_moved and current_price <= entry_price - sl_move_trigger:
                sl = entry_price - sl_after_move
                sl_moved = True

            if current_price >= sl:
                loss = abs(entry_price - sl) * lot_size * contract_size
                current_balance -= loss
                cumulative_loss += loss
                profit = -loss
                outcome = "LOSS"
                exit_time = candle["datetime"]
                break

            floating_profit = (entry_price - current_price) * lot_size * contract_size
            if floating_profit >= current_balance * profit_target_pct:
                current_balance += floating_profit
                cumulative_loss = 0
                profit = floating_profit
                outcome = "WIN"
                exit_time = candle["datetime"]
                break

    # Record the trade if it was closed
    if outcome in ["WIN", "LOSS"]:
        results.append({
            "Entry Time": entry_time,
            "Signal": signal_type,
            "Entry Price": entry_price,
            "Lot Size": round(lot_size, 4),
            "SL Exit Price": round(sl, 2),
            "SL Moved": sl_moved,
            "Exit Time": exit_time,
            "Outcome": outcome,
            "Profit": round(profit, 2),
            "Balance After Trade": round(current_balance, 2)
        })

# Save to CSV
results_df = pd.DataFrame(results)
results_df.to_csv("backtest_final_strategy.csv", index=False)

print("✅ Backtest complete with custom SL logic. Results saved to 'backtest_final_strategy.csv'")
