# src/load.py
import pandas as pd

REQUIRED_COLUMNS = ["date", "region", "product", "orders", "sales", "profit"]
NUMERIC_COLUMNS = ["orders", "sales", "profit"]


def load_data(path):
    """Read the Excel file, validate it, and return a clean DataFrame."""
    df = pd.read_excel(path)

    # 1. normalize column names
    df.columns = [str(c).strip().lower() for c in df.columns]

    # 2. check required columns
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Excel file is missing required columns: {missing}")

    # 3. convert types (bad values become NaN / NaT)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for col in NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 4. drop rows with missing values, then duplicates
    before = len(df)
    df = df.dropna(subset=REQUIRED_COLUMNS).drop_duplicates()
    dropped = before - len(df)
    if dropped > 0:
        print(f"[load] dropped {dropped} invalid or duplicate rows")

    if df.empty:
        raise ValueError("No valid rows left after cleaning")

    return df


def daily_totals(df, metrics):
    """One row per calendar day with the summed metrics. Missing days become NaN."""
    return df.groupby("date")[list(metrics)].sum().asfreq("D")