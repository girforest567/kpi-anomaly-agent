from src.load import load_data, daily_totals

df = load_data("data/sales.xlsx")
print(df.shape)                      # (4380, 6)
print(df.dtypes)                     # date should be datetime64, others numbers

daily = daily_totals(df, ["sales", "profit", "orders"])
print(daily.shape)                   # (365, 3)
print(daily.head())