# tests/test_load.py
import pandas as pd
import pytest

from src.load import load_data, daily_totals


def test_loads_expected_shape():
    df = load_data("data/sales.xlsx")
    assert df.shape == (4380, 6)


def test_daily_totals_has_one_row_per_day():
    df = load_data("data/sales.xlsx")
    daily = daily_totals(df, ["sales", "profit", "orders"])
    assert daily.shape == (365, 3)


def test_missing_column_raises_clear_error(tmp_path):
    bad = pd.DataFrame({"date": ["2025-01-01"], "region": ["North"], "sales": [100]})
    path = tmp_path / "bad.xlsx"
    bad.to_excel(path, index=False)
    with pytest.raises(ValueError, match="missing required columns"):
        load_data(path)


def test_duplicates_and_bad_rows_are_dropped(tmp_path):
    row = {"date": "2025-01-01", "region": "North", "product": "Office",
           "orders": 5, "sales": 100.0, "profit": 10.0}
    bad_row = dict(row, date="not a date")
    df = pd.DataFrame([row, row, bad_row])      # one duplicate + one invalid date
    path = tmp_path / "messy.xlsx"
    df.to_excel(path, index=False)
    assert len(load_data(path)) == 1