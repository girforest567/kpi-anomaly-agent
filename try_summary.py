from src.load import load_data, daily_totals
from src.detect import detect_all
from src.drivers import explain
from src.summarize import summarize

METRICS = ["sales", "profit", "orders"]
df = load_data("data/sales.xlsx")
daily = daily_totals(df, METRICS)
found = detect_all(daily, METRICS)

for date, metric in [("2025-03-12", "sales"), ("2025-05-20", "sales"), ("2025-09-15", "profit")]:
    row = found[(found["date"] == date) & (found["metric"] == metric)].iloc[0]
    drivers = explain(df, row["date"], metric, row["expected"])
    text, facts, source = summarize(row, drivers, use_llm=True)
    print(f"[{source}] {text}\n")