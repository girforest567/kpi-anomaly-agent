# tests/test_summarize.py
import pytest

from src.load import load_data, daily_totals
from src.detect import detect_all
from src.drivers import explain
from src import summarize as S

METRICS = ["sales", "profit", "orders"]


@pytest.fixture(scope="module")
def case():
    df = load_data("data/sales.xlsx")
    found = detect_all(daily_totals(df, METRICS), METRICS)
    row = found[(found["date"] == "2025-03-12") & (found["metric"] == "sales")].iloc[0]
    return row, explain(df, row["date"], "sales", row["expected"])


def test_template_mentions_the_right_driver(case):
    row, drivers = case
    text, facts, source = S.summarize(row, drivers, use_llm=False)
    assert source == "template"
    assert "West" in text and "fell" in text


def test_template_numbers_are_grounded(case):
    row, drivers = case
    facts = S.build_facts(row, drivers)
    assert S.numbers_are_grounded(S.template_summary(facts), facts)


def test_invented_number_is_rejected(case):
    row, drivers = case
    facts = S.build_facts(row, drivers)
    assert not S.numbers_are_grounded("Sales fell 77.7% because of West.", facts)


def test_falls_back_to_template_when_llm_makes_up_numbers(case, monkeypatch):
    row, drivers = case
    monkeypatch.setattr(S, "llm_summary", lambda facts, model: "Sales fell 77.7% in West.")
    text, _, source = S.summarize(row, drivers, use_llm=True)
    assert source == "template"


def test_uses_llm_text_when_numbers_are_valid(case, monkeypatch):
    row, drivers = case
    facts = S.build_facts(row, drivers)
    good = f"Sales fell {abs(facts['pct_change'])}% on {facts['date']}, driven by West."
    monkeypatch.setattr(S, "llm_summary", lambda f, model: good)
    text, _, source = S.summarize(row, drivers, use_llm=True)
    assert source == "llm" and text == good


def test_no_api_key_means_template(case, monkeypatch):
    row, drivers = case
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    _, _, source = S.summarize(row, drivers, use_llm=True)
    assert source == "template"