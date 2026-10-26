import pandas as pd
from src.load import load_data, daily_totals
from src.detect import detect_all
from src.drivers import explain

METRICS = ["sales", "profit", "orders"]
df = load_data("data/sales.xlsx")
daily = daily_totals(df, METRICS)
found = detect_all(daily, METRICS)

pd.set_option("display.width", 200)
for date, metric in [("2025-03-12", "sales"), ("2025-05-20", "sales"), ("2025-09-15", "profit")]:
    row = found[(found["date"] == date) & (found["metric"] == metric)].iloc[0]
    d = explain(df, row["date"], metric, row["expected"])
    print(f"\n=== {metric} on {date}: {row['pct_change']*100:+.1f}% vs expected ===")
    print("By region:\n", d["by_region"].round(2).to_string(index=False))
    print("By product:\n", d["by_product"].round(2).to_string(index=False))
    print("Top segments:\n", d["segments"].round(2).to_string(index=False))