# tests/test_main.py
import pytest
import yaml

from src import main as M

CFG = {
    "data_path": "data/sales.xlsx",
    "metrics": ["sales", "profit", "orders"],
    "detection": {"window": 28, "warn_z": 3.0, "crit_z": 4.0, "min_pct": 0.10},
    "lookback_days": 3,
    "max_alerts_per_email": 5,
    "llm": {"enabled": False, "model": "claude-sonnet-5-5"},
    "email": {"recipients": ["x@example.com"], "subject_prefix": "[KPI Alert]"},
}


@pytest.fixture(autouse=True)
def no_smtp(monkeypatch):
    for k in ["SMTP_USER", "SMTP_PASSWORD", "ALERT_RECIPIENTS", "ANTHROPIC_API_KEY"]:
        monkeypatch.delenv(k, raising=False)


def run(tmp_path, **kw):
    return M.run(CFG, log_path=str(tmp_path / "log.csv"), out_dir=str(tmp_path), **kw)


def test_reports_the_black_friday_anomalies(tmp_path):
    items = run(tmp_path, as_of="2025-11-30", lookback=5)
    assert {i["anomaly"]["metric"] for i in items} == {"sales", "profit", "orders"}
    assert (tmp_path / "email_preview.html").exists()


def test_second_run_does_not_repeat_alerts(tmp_path):
    assert len(run(tmp_path, as_of="2025-11-30", lookback=5)) == 3
    assert run(tmp_path, as_of="2025-11-30", lookback=5) == []


def test_quiet_period_sends_nothing(tmp_path):
    assert run(tmp_path, as_of="2025-06-01", lookback=3) == []
    assert not (tmp_path / "email_preview.html").exists()


def test_alert_cap_is_respected(tmp_path):
    cfg = dict(CFG, max_alerts_per_email=2)
    items = M.run(cfg, as_of="2025-12-31", lookback=365,
                  log_path=str(tmp_path / "log.csv"), out_dir=str(tmp_path))
    assert len(items) == 2


def test_failure_returns_exit_code_1(tmp_path, capsys):
    bad = dict(CFG, data_path="data/does_not_exist.xlsx")
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(bad))
    assert M.main(["--config", str(path)]) == 1
    assert "PIPELINE FAILED" in capsys.readouterr().out