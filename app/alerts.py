import smtplib
from email.message import EmailMessage

from .config import ALERT_FROM, ALERT_TO, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER


def send_drop_email(subject: str, body: str) -> str:
    """Return channel used: smtp or log."""
    if not SMTP_HOST:
        print(f"[alert-log] To: {ALERT_TO}\nSubject: {subject}\n{body}\n")
        return "log"
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = ALERT_FROM
    msg["To"] = ALERT_TO
    msg.set_content(body)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as smtp:
        smtp.starttls()
        if SMTP_USER:
            smtp.login(SMTP_USER, SMTP_PASSWORD)
        smtp.send_message(msg)
    return "smtp"
