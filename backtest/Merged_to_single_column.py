import pandas as pd

# Read the raw CSV where everything is in one column
df = pd.read_csv("input.csv", header=None)

# Split by tab or space
df_split = df[0].str.split(r"\s+", expand=True)

# Rename columns

df_split.columns = ["Date", "Time", "Signal", "Price", "Open", "High", "Low", "Close"]

# Save to new CSV
df_split.to_csv("formatted_output.csv", index=False)
print("✅ CSV has been fixed and saved as 'formatted_output.csv'")
