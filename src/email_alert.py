import os
import ssl
import smtplib
from email.message import EmailMessage

def send_email_alert(status, confidence, risk_level="HIGH", risk_score=0, latitude=None, longitude=None, timestamp=None):
    sender_email = os.getenv("FIREGUARD_EMAIL", "").strip()
    app_password = os.getenv("FIREGUARD_APP_PASSWORD", "").strip()

    if not sender_email or not app_password:
        return False, "Email credentials are missing."

    msg = EmailMessage()
    msg["Subject"] = f"FIREGUARD AI ALERT: {status}"
    msg["From"] = sender_email
    msg["To"] = sender_email
    msg.set_content(
        f"Status: {status}\nConfidence: {confidence:.1%}\nRisk: {risk_level}\nRisk score: {risk_score}\nLocation: {latitude}, {longitude}\nTimestamp: {timestamp}"
    )

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30, context=ssl.create_default_context()) as server:
            server.login(sender_email, app_password)
            server.send_message(msg)
        return True, "Email alert sent successfully."
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"
