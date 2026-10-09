
import os
import ssl
import smtplib
from email.message import EmailMessage

import streamlit as st


def send_email_alert(
    status,
    confidence,
    risk_level="HIGH",
    risk_score=0,
    latitude=None,
    longitude=None,
    timestamp=None,
):
    sender_email = "akulamonalisa@gmail.com"
    receiver_email = "akulamonalisa123@gmail.com"
    app_password = "nwcuunobrdqkuqwv"

    # Read password securely from Streamlit Secrets
    try:
        config = st.secrets.get("email", {})
        sender_email = str(
            config.get("sender", sender_email)
        ).strip()
        receiver_email = str(
            config.get("receiver", receiver_email)
        ).strip()
        app_password = str(
            config.get("password", "")
        ).replace(" ", "").strip()
    except Exception:
        pass

    # Support local environment variables too
    app_password = app_password or os.getenv(
        "FIREGUARD_APP_PASSWORD", ""
    ).replace(" ", "").strip()

    if not sender_email or not receiver_email or not app_password:
        return False, (
            "Email credentials missing. Check Streamlit Cloud Secrets."
        )

    msg = EmailMessage()
    msg["Subject"] = f"FIREGUARD AI ALERT: {status}"
    msg["From"] = sender_email
    msg["To"] = receiver_email

    msg.set_content(
        f"FIREGUARD AI ALERT\n\n"
        f"Status: {status}\n"
        f"Confidence: {float(confidence):.1%}\n"
        f"Risk level: {risk_level}\n"
        f"Risk score: {risk_score}\n"
        f"Location: {latitude}, {longitude}\n"
        f"Timestamp: {timestamp}\n"
    )

    try:
        context = ssl.create_default_context()

        with smtplib.SMTP_SSL(
            "smtp.gmail.com",
            465,
            timeout=30,
            context=context,
        ) as server:
            server.login(sender_email, app_password)
            server.send_message(msg)

        return True, f"Email alert sent to {receiver_email}."

    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"
