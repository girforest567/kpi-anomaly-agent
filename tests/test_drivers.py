# tests/test_drivers.py
import pytest

from src.load import load_data, daily_totals
from src.detect import detect_all
from src.drivers import explain

METRICS = ["sales", "profit", "orders"]


@pytest.fixture(scope="module")
def setup():
    df = load_data("data/sales.xlsx")
    daily = daily_totals(df, METRICS)
    return df, detect_all(daily, METRICS)


def get(setup, date, metric):
    df, found = setup
    row = found[(found["date"] == date) & (found["metric"] == metric)].iloc[0]
    return explain(df, row["date"], metric, row["expected"])


def test_west_outage_is_blamed_on_west(setup):
    d = get(setup, "2025-03-12", "sales")
    assert d["by_region"].iloc[0]["segment"] == "West"
    assert d["by_region"].iloc[0]["share_of_change"] > 0.8


def test_promo_spike_is_blamed_on_electronics(setup):
    d = get(setup, "2025-05-20", "sales")
    assert d["by_product"].iloc[0]["segment"] == "Electronics"


def test_profit_collapse_is_blamed_on_furniture(setup):
    d = get(setup, "2025-09-15", "profit")
    assert d["by_product"].iloc[0]["segment"] == "Furniture"


def test_segment_deltas_add_up_to_total_change(setup):
    df, found = setup
    row = found[(found["date"] == "2025-07-08") & (found["metric"] == "sales")].iloc[0]
    d = explain(df, row["date"], "sales", row["expected"], top_n=100)   # all segments
    total_change = row["actual"] - row["expected"]
    assert d["segments"]["delta"].sum() == pytest.approx(total_change, rel=1e-6)