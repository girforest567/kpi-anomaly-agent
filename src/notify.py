# src/notify.py
import base64
import html
import io
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

import matplotlib
matplotlib.use("Agg")                      # draw charts without opening a window
import matplotlib.pyplot as plt

COLORS = {"critical": "#c0392b", "warning": "#e67e22"}


def make_chart(daily, metric, date, days=60):
    """Line chart of the last `days` days with the anomaly as a red dot. Returns PNG bytes."""
    series = daily[metric]
    window = series[:date].tail(days)
    fig, ax = plt.subplots(figsize=(6.5, 2.6))
    ax.plot(window.index, window.values, color="#2c3e50", linewidth=1.6)
    ax.scatter([date], [series[date]], color="#c0392b", zorder=3, s=45)
    ax.set_title(f"{metric.capitalize()} - last {days} days", fontsize=10)
    ax.grid(alpha=0.25)
    fig.autofmt_xdate()
    fig.tight_layout()
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=110)
    plt.close(fig)                         # free memory
    return buffer.getvalue()


def build_html(items):
    """items = list of {"anomaly": row, "summary": str, "facts": dict}"""
    parts = ["<div style='font-family:Arial,sans-serif;max-width:680px'>",
             f"<h2>KPI anomaly report - {len(items)} alert(s)</h2>"]
    for i, item in enumerate(items):
        a, f = item["anomaly"], item["facts"]
        color = COLORS[a["severity"]]
        rows = "".join(
            f"<tr><td>{html.escape(s['segment'])}</td><td>{s['pct_vs_expected']}%</td>"
            f"<td>{s['share_of_change_pct']}%</td></tr>"
            for s in f["top_segments"]
        )
        parts.append(
            f"<div style='border-left:5px solid {color};padding:8px 14px;margin:18px 0;background:#fafafa'>"
            f"<b style='color:{color}'>{a['severity'].upper()}</b> &middot; {html.escape(f['metric'])}"
            f" &middot; {f['date']} &middot; {f['pct_change']:+}% vs expected (z={a['z']:.1f})"
            f"<p>{html.escape(item['summary'])}</p>"
            f"<table cellpadding='4' border='1' style='border-collapse:collapse;font-size:13px'>"
            f"<tr><th>Top driver</th><th>vs expected</th><th>share of change</th></tr>{rows}</table>"
            f"<img src='cid:chart{i}' style='margin-top:10px;max-width:100%'></div>"
        )
    parts.append("</div>")
    return "".join(parts)


def build_message(subject, html_body, charts, sender, recipients):
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, sender, ", ".join(recipients)
    msg.set_content("This alert needs an HTML-capable email client.")     # plain-text fallback
    msg.add_alternative(html_body, subtype="html")
    html_part = msg.get_payload()[1]
    for i, png in enumerate(charts):
        html_part.add_related(png, "image", "png", cid=f"<chart{i}>")      # embed chart inline
    return msg


def save_preview(html_body, charts, out_dir):
    """Browser-viewable copy with charts embedded. Perfect for README screenshots."""
    preview = html_body
    for i, png in enumerate(charts):
        data_uri = "data:image/png;base64," + base64.b64encode(png).decode()
        preview = preview.replace(f"cid:chart{i}", data_uri)
    path = Path(out_dir) / "email_preview.html"
    path.write_text(preview, encoding="utf-8")
    return path


def send_alert(items, daily, cfg, out_dir="outputs"):
    """Build the email. Send it if SMTP settings exist, otherwise dry-run. Returns True if sent."""
    Path(out_dir).mkdir(exist_ok=True)
    charts = [make_chart(daily, it["anomaly"]["metric"], it["anomaly"]["date"]) for it in items]
    body = build_html(items)

    worst = "CRITICAL" if any(it["anomaly"]["severity"] == "critical" for it in items) else "WARNING"
    subject = f"{cfg['email']['subject_prefix']} {worst}: {len(items)} KPI anomaly(ies) detected"

    recipients = os.getenv("ALERT_RECIPIENTS", ",".join(cfg["email"]["recipients"]))
    recipients = [r.strip() for r in recipients.split(",") if r.strip()]
    user, password = os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD")
    sender = os.getenv("EMAIL_FROM", user or "alerts@example.com")

    preview = save_preview(body, charts, out_dir)
    if not (user and password):
        print(f"[notify] SMTP not configured -> DRY RUN. Preview saved: {preview}")
        return False

    msg = build_message(subject, body, charts, sender, recipients)
    with smtplib.SMTP(os.getenv("SMTP_HOST", "smtp.gmail.com"), int(os.getenv("SMTP_PORT", "587"))) as server:
        server.starttls()
        server.login(user, password)
        server.send_message(msg)
    print(f"[notify] email sent to {recipients}")
    return True