# src/drivers.py
import pandas as pd


def contributions(df, date, metric, expected_total, group_cols, window=28, top_n=3):
    """Which segments (grouped by group_cols) explain the gap between
    the actual total and the expected total on `date`?"""
    date = pd.Timestamp(date)

    # 1. history = the previous `window` days (NOT including the anomaly day)
    history = df[(df["date"] < date) & (df["date"] >= date - pd.Timedelta(days=window))]
    today = df[df["date"] == date]

    # 2. each segment's normal share of the total (e.g. West = 25%)
    share = history.groupby(group_cols)[metric].sum()
    share = share / share.sum()

    # 3. what each segment actually did today
    actual = today.groupby(group_cols)[metric].sum()

    # 4. line both up on the same segments (fill gaps with 0)
    segments = share.index.union(actual.index)
    share = share.reindex(segments, fill_value=0)
    actual = actual.reindex(segments, fill_value=0)

    # 5. expected per segment = its normal share x the expected total
    expected = share * expected_total
    delta = actual - expected                    # deltas add up to the total change
    total_delta = delta.sum()

    names = [" / ".join(map(str, s)) if isinstance(s, tuple) else str(s) for s in segments]
    out = pd.DataFrame({
        "segment": names,
        "actual": actual.values,
        "expected": expected.values,
        "delta": delta.values,
        "pct_vs_expected": (delta / expected.replace(0, float("nan"))).values,
        "share_of_change": (delta / total_delta).values if total_delta != 0 else 0.0,
    })

    # 6. biggest movers in the SAME direction as the total change come first
    direction = 1 if total_delta >= 0 else -1
    out = out.assign(_rank=out["delta"] * direction).sort_values("_rank", ascending=False)
    return out.drop(columns="_rank").head(top_n).reset_index(drop=True)


def explain(df, date, metric, expected_total, window=28, top_n=3):
    """Explain one anomaly three ways: by segment, by region, by product."""
    return {
        "segments": contributions(df, date, metric, expected_total, ["region", "product"], window, top_n),
        "by_region": contributions(df, date, metric, expected_total, ["region"], window, top_n),
        "by_product": contributions(df, date, metric, expected_total, ["product"], window, top_n),
    }