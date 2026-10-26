# src/summarize.py
import json
import os
import re


def build_facts(anomaly, drivers):
    """Collect every number the summary may use. Python computes them, never the LLM."""
    return {
        "metric": anomaly["metric"],
        "date": str(anomaly["date"].date()),
        "direction": anomaly["direction"],
        "severity": anomaly["severity"],
        "actual": round(float(anomaly["actual"]), 1),
        "expected": round(float(anomaly["expected"]), 1),
        "pct_change": round(float(anomaly["pct_change"]) * 100, 1),
        "top_region": drivers["by_region"].iloc[0]["segment"],
        "top_region_share_pct": round(float(drivers["by_region"].iloc[0]["share_of_change"]) * 100, 1),
        "top_product": drivers["by_product"].iloc[0]["segment"],
        "top_product_share_pct": round(float(drivers["by_product"].iloc[0]["share_of_change"]) * 100, 1),
        "top_segments": [
            {
                "segment": r.segment,
                "pct_vs_expected": round(float(r.pct_vs_expected) * 100, 1),
                "share_of_change_pct": round(float(r.share_of_change) * 100, 1),
            }
            for r in drivers["segments"].itertuples()
        ],
    }


def template_summary(f):
    """Always-works summary. No LLM needed."""
    word = "rose" if f["direction"] == "up" else "fell"
    top = f["top_segments"][0]
    return (
        f"{f['metric'].capitalize()} {word} {abs(f['pct_change'])}% versus the expected level "
        f"on {f['date']} ({f['actual']} actual vs {f['expected']} expected). "
        f"The largest single driver was {top['segment']} ({top['pct_vs_expected']}% vs its normal level), "
        f"and {f['top_product']} accounted for {f['top_product_share_pct']}% of the change by product. "
        f"Check {top['segment']} first for operational, pricing or stock issues."
    )


def numbers_are_grounded(text, facts):
    """Safety check: every number in the text must come from the facts.
    Decimals must match exactly. Whole numbers may be a rounded fact (65.1 -> 65)."""
    exact = set(re.findall(r"\d+(?:\.\d+)?", json.dumps(facts)))
    rounded = {str(int(round(float(n)))) for n in exact}
    for n in re.findall(r"\d+(?:\.\d+)?", text):
        if "." in n:
            if n not in exact:
                return False
        elif n not in exact and n not in rounded:
            return False
    return True


def llm_summary(facts, model):
    """Ask Claude to put the facts into words. Returns None on any problem."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        return None
    try:
        import anthropic
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model=model,
            max_tokens=300,
            system=(
                "You are a business analyst writing a KPI alert. Use ONLY the numbers in the JSON. "
                "Never invent, recompute or convert numbers. Write 3 short plain-English sentences: "
                "what happened, the main driver, one suggested next check. No markdown."
            ),
            messages=[{"role": "user", "content": json.dumps(facts)}],
        )
        return msg.content[0].text.strip()
    except Exception as e:
        print(f"[summarize] LLM call failed ({type(e).__name__}); using template")
        return None


def summarize(anomaly, drivers, use_llm=True, model="claude-sonnet-5-5"):
    """Return (summary_text, facts, source) where source is 'llm' or 'template'."""
    facts = build_facts(anomaly, drivers)
    if use_llm:
        text = llm_summary(facts, model)
        if text and numbers_are_grounded(text, facts):
            return text, facts, "llm"
        if text:
            print("[summarize] LLM used numbers not in the facts; using template")
    return template_summary(facts), facts, "template"