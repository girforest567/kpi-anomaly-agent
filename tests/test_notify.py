# tests/test_notify.py
import pytest

from src.load import load_data, daily_totals
from src.detect import detect_all
from src.drivers import explain
from src.summarize import summarize
from src import notify as N

METRICS = ["sales", "profit", "orders"]
CFG = {"email": {"subject_prefix": "[KPI Alert]", "recipients": ["boss@example.com"]}}


@pytest.fixture(scope="module")
def data():
    df = load_data("data/sales.xlsx")
    daily = daily_totals(df, METRICS)
    found = detect_all(daily, METRICS)
    row = found[(found["date"] == "2025-03-12") & (found["metric"] == "sales")].iloc[0]
    text, facts, _ = summarize(row, explain(df, row["date"], "sales", row["expected"]), use_llm=False)
    return daily, [{"anomaly": row, "summary": text, "facts": facts}]


def clear_smtp_env(monkeypatch):
    for k in ["SMTP_USER", "SMTP_PASSWORD", "ALERT_RECIPIENTS", "EMAIL_FROM"]:
        monkeypatch.delenv(k, raising=False)


def test_chart_is_a_png(data):
    daily, items = data
    png = N.make_chart(daily, "sales", items[0]["anomaly"]["date"])
    assert png.startswith(b"\x89PNG")


def test_html_contains_severity_summary_and_driver(data):
    _, items = data
    body = N.build_html(items)
    assert "CRITICAL" in body and "West" in body and "cid:chart0" in body


def test_html_escapes_dangerous_text(data):
    _, items = data
    evil = [{**items[0], "summary": "<script>alert(1)</script>"}]
    assert "<script>" not in N.build_html(evil)


def test_message_has_html_and_embedded_chart(data):
    daily, items = data
    png = N.make_chart(daily, "sales", items[0]["anomaly"]["date"])
    msg = N.build_message("Subj", N.build_html(items), [png], "a@x.com", ["b@x.com"])
    kinds = [p.get_content_type() for p in msg.walk()]
    assert "text/html" in kinds and "image/png" in kinds
    assert msg["To"] == "b@x.com"


def test_dry_run_when_no_credentials(data, tmp_path, monkeypatch):
    daily, items = data
    clear_smtp_env(monkeypatch)
    sent = N.send_alert(items, daily, CFG, out_dir=str(tmp_path))
    assert sent is False
    assert (tmp_path / "email_preview.html").exists()


def test_sends_email_when_credentials_exist(data, tmp_path, monkeypatch):
    daily, items = data
    clear_smtp_env(monkeypatch)
    monkeypatch.setenv("SMTP_USER", "me@gmail.com")
    monkeypatch.setenv("SMTP_PASSWORD", "app-password")

    calls = []

    class FakeSMTP:
        def __init__(self, host, port): calls.append(("connect", host, port))
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def starttls(self): calls.append(("starttls",))
        def login(self, u, p): calls.append(("login", u))
        def send_message(self, msg): calls.append(("send", msg["Subject"], msg["To"]))

    monkeypatch.setattr(N.smtplib, "SMTP", FakeSMTP)
    assert N.send_alert(items, daily, CFG, out_dir=str(tmp_path)) is True
    assert ("login", "me@gmail.com") in calls
    assert any(c[0] == "send" and "CRITICAL" in c[1] and c[2] == "boss@example.com" for c in calls)