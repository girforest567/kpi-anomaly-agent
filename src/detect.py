# src/detect.py
import pandas as pd


def weekday_factors(series):
    """How strong each weekday normally is, e.g. Saturday = 1.25."""
    weekly_avg = series.rolling(7, center=True, min_periods=4).mean()
    ratio = series / weekly_avg
    return ratio.groupby(series.index.day_of_week).median()


def detect_metric(series, window=28, warn_z=3.0, crit_z=4.0, min_pct=0.10):
    """Return a DataFrame of anomalous days for ONE metric (a daily Series)."""
    # 1. remove the weekly pattern
    factors = weekday_factors(series)
    factor_per_day = pd.Series([factors[d] for d in series.index.day_of_week], index=series.index)
    adjusted = series / factor_per_day

    # 2. baseline from the PREVIOUS days only (shift(1))
    mean = adjusted.rolling(window, min_periods=14).mean().shift(1)
    std = adjusted.rolling(window, min_periods=14).std().shift(1)

    # 3. z-score, expected value, % change
    z = (adjusted - mean) / std
    expected = mean * factor_per_day
    pct_change = (series - expected) / expected

    # 4. flag: big z-score AND big enough change
    flagged = (z.abs() >= warn_z) & (pct_change.abs() >= min_pct)

    result = pd.DataFrame({
        "actual": series,
        "expected": expected,
        "pct_change": pct_change,
        "z": z,
    })[flagged]
    result["direction"] = result["z"].apply(lambda v: "up" if v > 0 else "down")
    result["severity"] = result["z"].apply(lambda v: "critical" if abs(v) >= crit_z else "warning")
    return result


def detect_all(daily, metrics, **kwargs):
    """Run detect_metric for every metric and stack the results."""
    parts = []
    for m in metrics:
        r = detect_metric(daily[m], **kwargs)
        r.insert(0, "metric", m)
        parts.append(r)
    out = pd.concat(parts)
    out.index.name = "date"
    return out.reset_index().sort_values(["date", "metric"]).reset_index(drop=True)