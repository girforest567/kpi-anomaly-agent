# tests/test_detect.py
import pandas as pd
import pytest

from src.load import load_data, daily_totals
from src.detect import detect_all

METRICS = ["sales", "profit", "orders"]


@pytest.fixture(scope="module")
def planted_dates():
    with open("data/answer_key.txt") as f:
        return {line.split(" - ")[0] for line in f.read().splitlines()}


@pytest.fixture(scope="module")
def found():
    df = load_data("data/sales.xlsx")
    daily = daily_totals(df, METRICS)
    return detect_all(daily, METRICS)


def found_dates(found):
    return set(found["date"].dt.strftime("%Y-%m-%d"))


def test_catches_every_planted_anomaly(found, planted_dates):
    missed = planted_dates - found_dates(found)
    assert not missed, f"Missed anomalies: {missed}"


def test_few_false_alarms(found, planted_dates):
    false_alarms = found_dates(found) - planted_dates
    assert len(false_alarms) <= 2, f"Too many false alarms: {false_alarms}"


def test_direction_is_correct(found):
    july = found[(found["metric"] == "sales") & (found["date"] == "2025-07-08")].iloc[0]
    may = found[(found["metric"] == "sales") & (found["date"] == "2025-05-20")].iloc[0]
    assert july["direction"] == "down"
    assert may["direction"] == "up"


def test_profit_only_anomaly_not_flagged_in_sales(found):
    sept = found[found["date"] == "2025-09-15"]
    assert list(sept["metric"]) == ["profit"]


def test_no_alerts_in_warmup_period(found):
    assert (found["date"] >= pd.Timestamp("2025-01-15")).all()


def test_severity_labels_are_valid(found):
    assert set(found["severity"]) <= {"warning", "critical"}


def test_baseline_excludes_the_day_itself():
    """If shift(1) is removed, the spike leaks into its own baseline."""
    import numpy as np
    from src.detect import detect_metric

    rng = np.random.default_rng(0)
    idx = pd.date_range("2025-01-01", periods=60, freq="D")
    series = pd.Series(100 + rng.normal(0, 1, 60), index=idx)
    series.iloc[40] = 200                                  # one big spike
    result = detect_metric(series)
    spike_day = idx[40]
    assert spike_day in result.index
    assert abs(result.loc[spike_day, "expected"] - 100) < 1.0