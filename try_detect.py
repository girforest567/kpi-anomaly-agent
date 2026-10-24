from src.load import load_data, daily_totals
from src.detect import detect_all

METRICS = ["sales", "profit", "orders"]
df = load_data("data/sales.xlsx")
daily = daily_totals(df, METRICS)

found = detect_all(daily, METRICS)
show = found.copy()
show["pct_change"] = (show["pct_change"] * 100).round(1)
show["z"] = show["z"].round(1)
print(show[["date", "metric", "pct_change", "z", "severity"]].to_string())

planted = [l.split(" - ")[0] for l in open("data/answer_key.txt").read().splitlines()]
found_dates = set(found["date"].dt.strftime("%Y-%m-%d"))
caught = [d for d in planted if d in found_dates]
false_alarms = sorted(found_dates - set(planted))
print(f"\nCaught {len(caught)} of {len(planted)} planted anomalies")
print("Missed:", [d for d in planted if d not in found_dates])
print("False alarm dates:", false_alarms)