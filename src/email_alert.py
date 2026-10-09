
import os
import ssl
import smtplib
import streamlit as st
from email.message import EmailMessage


def send_email_alert(
    status,
    confidence,
    risk_level="HIGH",
    risk_score=0,
    latitude=None,
    longitude=None,
    timestamp=None,
):
    try:
        email_config = st.secrets.get("email", {})

        sender_email = email_config.get("sender", "").strip()
        app_password = email_config.get("password", "").replace(" ", "").strip()
        receiver_email = email_config.get("receiver", "").strip()

        if not sender_email or not app_password or not receiver_email:
            return False, "Email settings missing in Streamlit Secrets."

        msg = EmailMessage()
        msg["Subject"] = f"FIREGUARD AI ALERT: {status}"
        msg["From"] = sender_email
        msg["To"] = receiver_email

        msg.set_content(
            f"FIREGUARD AI - FIRE/SMOKE ALERT\n\n"
            f"Status: {status}\n"
            f"Confidence: {confidence:.1%}\n"
            f"Risk level: {risk_level}\n"
            f"Risk score: {risk_score}\n"
            f"Location: {latitude}, {longitude}\n"
            f"Timestamp: {timestamp}\n"
        )

        with smtplib.SMTP_SSL(
            "smtp.gmail.com",
            465,
            timeout=30,
            context=ssl.create_default_context(),
        ) as server:
            server.login(sender_email, app_password)
            server.send_message(msg)

        return True, "Email alert sent successfully."

    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"
