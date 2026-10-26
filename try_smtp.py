# try_smtp.py  (diagnostic only - never prints the password)
import os
import smtplib
import ssl

user = os.getenv("SMTP_USER")
password = os.getenv("SMTP_PASSWORD")
host = os.getenv("SMTP_HOST", "smtp.gmail.com")
print("user set:", bool(user), "| password length:", len(password or ""))


def attempt(label, make_server):
    try:
        with make_server() as s:
            s.ehlo()
            if label.startswith("587"):
                s.starttls(context=ssl.create_default_context())
                s.ehlo()
            s.login(user, password)
        print(label, "-> LOGIN OK")
    except Exception as e:
        print(label, "-> FAILED:", type(e).__name__)


attempt("587 STARTTLS", lambda: smtplib.SMTP(host, 587, timeout=20))
attempt("465 SSL", lambda: smtplib.SMTP_SSL(host, 465, timeout=20, context=ssl.create_default_context()))