# src/main.py
import argparse
import sys
import traceback
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml

from src.detect import detect_all
from src.drivers import explain
from src.load import daily_totals, load_data
from src.notify import send_alert, send_failure, smtp_configured
from src.summarize import summarize


def load_config(path):
    with open(path) as f:
        return yaml.safe_load(f)


def already_alerted(log_path, will_send):
    """(date, metric) pairs we must not alert on again.
    A real run only trusts rows that were really emailed; a dry run trusts every row."""
    if not Path(log_path).exists():
        return set()
    log = pd.read_csv(log_path)
    if will_send:
        log = log[log["emailed"].astype(str) == "True"]
    return set(zip(log["date"], log["metric"]))


def write_log(items, sent, log_path):
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = pd.DataFrame([{
        "run_time": datetime.now().isoformat(timespec="seconds"),
        "date": str(i["anomaly"]["date"].date()),
        "metric": i["anomaly"]["metric"],
        "severity": i["anomaly"]["severity"],
        "z": round(float(i["anomaly"]["z"]), 2),
        "pct_change": round(float(i["anomaly"]["pct_change"]), 3),
        "emailed": sent,
    } for i in items])
    rows.to_csv(path, mode="a", header=not path.exists(), index=False)


def run(cfg, as_of=None, lookback=None, log_path="outputs/alerts_log.csv", out_dir="outputs"):
    # 1. load and detect
    df = load_data(cfg["data_path"])
    metrics = cfg["metrics"]
    daily = daily_totals(df, metrics)
    found = detect_all(daily, metrics, **cfg["detection"])
    print(f"[main] {len(found)} anomalies found in the full history")

    # 2. keep only the recent window
    as_of = pd.Timestamp(as_of) if as_of else daily.index.max()
    lookback = lookback or cfg["lookback_days"]
    recent = found[(found["date"] <= as_of) & (found["date"] > as_of - pd.Timedelta(days=lookback))]

    # 3. drop anything we already alerted on
    seen = already_alerted(log_path, will_send=smtp_configured())
    keep = [(str(d.date()), m) not in seen for d, m in zip(recent["date"], recent["metric"])]
    new = recent[keep]
    if new.empty:
        print("[main] nothing new to report - no email sent")
        return []

    # 4. most extreme first, capped so the inbox is not flooded
    new = new.reindex(new["z"].abs().sort_values(ascending=False).index)
    new = new.head(cfg["max_alerts_per_email"])

    # 5. explain and summarize each alert
    items = []
    for _, row in new.iterrows():
        drivers = explain(df, row["date"], row["metric"], row["expected"], window=cfg["detection"]["window"])
        text, facts, source = summarize(row, drivers, cfg["llm"]["enabled"], cfg["llm"]["model"])
        items.append({"anomaly": row, "summary": text, "facts": facts})

    # 6. email (or dry run), then log
    sent = send_alert(items, daily, cfg, out_dir=out_dir)
    write_log(items, sent, log_path)
    print(f"[main] {len(items)} alert(s) processed, emailed={sent}")
    return items


def main(argv=None):
    parser = argparse.ArgumentParser(description="KPI anomaly detection agent")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--as-of", help="treat this date as 'today' (YYYY-MM-DD); default = latest date in data")
    parser.add_argument("--lookback", type=int, help="override lookback_days from the config")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    try:
        run(cfg, args.as_of, args.lookback)
        return 0
    except Exception as e:
        traceback.print_exc()
        send_failure(f"{type(e).__name__}: {e}", cfg)
        return 1


if __name__ == "__main__":
    sys.exit(main())