import os
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)   # fixed seed = same data every time
dates = pd.date_range("2025-01-01", "2025-12-31")
regions = ["North", "South", "East", "West"]
products = ["Electronics", "Furniture", "Office"]

# ---------- Piece B: realism settings ----------
region_weight = {"North": 1.0, "South": 0.8, "East": 1.2, "West": 1.0}
product_weight = {"Electronics": 1.5, "Furniture": 1.0, "Office": 0.7}
weekday_mult = [1.0, 1.0, 1.02, 1.05, 1.15, 1.25, 0.95]   # Mon..Sun

# ---------- Piece C: profit margin per product ----------
margin = {"Electronics": 0.12, "Furniture": 0.08, "Office": 0.20}

# ---------- Piece D: the 5 planted anomalies (your answer key) ----------
ALL_REGIONS = regions
ALL_PRODUCTS = products
anomalies = [
    # date,        description,                       regions,      products,     sales/orders x, profit x
    ("2025-03-12", "West region outage",              ["West"],     ALL_PRODUCTS, 0.35, 0.35),
    ("2025-05-20", "Electronics promo spike",         ALL_REGIONS,  ["Electronics"], 1.8, 1.8),
    ("2025-07-08", "Sitewide payment failure",        ALL_REGIONS,  ALL_PRODUCTS, 0.60, 0.60),
    ("2025-09-15", "Furniture profit collapse",       ALL_REGIONS,  ["Furniture"], 1.0, 0.20),
    ("2025-11-27", "Black Friday surge",              ALL_REGIONS,  ALL_PRODUCTS, 1.7, 1.7),
]

# ---------- Build the rows ----------
rows = []
for d in dates:
    for r in regions:
        for p in products:
            sales = 1000
            sales = sales * region_weight[r]
            sales = sales * product_weight[p]
            sales = sales * weekday_mult[d.dayofweek]
            sales = sales * (1 + rng.normal(0, 0.08))          # random noise

            orders = sales / 80 * (1 + rng.normal(0, 0.03))
            profit = sales * margin[p] * (1 + rng.normal(0, 0.05))

            # apply planted anomalies
            for a_date, _, a_regions, a_products, f_sales, f_profit in anomalies:
                if d == pd.Timestamp(a_date) and r in a_regions and p in a_products:
                    sales = sales * f_sales
                    orders = orders * f_sales
                    profit = profit * f_profit

            rows.append([d, r, p, round(orders), round(sales, 2), round(profit, 2)])

df = pd.DataFrame(rows, columns=["date", "region", "product", "orders", "sales", "profit"])

# ---------- Piece E: save files ----------
os.makedirs("data", exist_ok=True)
df.to_excel("data/sales.xlsx", index=False)

with open("data/answer_key.txt", "w") as f:
    for a_date, desc, *_ in anomalies:
        f.write(f"{a_date} - {desc}\n")

        # ---------- Checks ----------
print("Shape:", df.shape)                       # expect (4380, 6)
print("Missing values:", df.isna().sum().sum()) # expect 0
print(df.head())
print("\nAverage sales by region:\n", df.groupby("region")["sales"].mean().round(0))
print("\nAverage sales by product:\n", df.groupby("product")["sales"].mean().round(0))

import matplotlib.pyplot as plt
df.groupby("date")["sales"].sum().plot(title="Total daily sales (look for 5 anomalies)")
plt.tight_layout()
plt.show()

