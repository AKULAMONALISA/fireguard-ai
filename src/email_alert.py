
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
    # Read email details only from Streamlit Secrets
    try:
        config = st.secrets["email"]
        sender_email = str(config["sender"]).strip()
        receiver_email = str(config["receiver"]).strip()
        app_password = str(config["password"]).replace(" ", "").strip()

    except (KeyError, FileNotFoundError):
        return False, (
            "Email settings missing. Configure sender, receiver, "
            "and password under Streamlit Cloud Secrets."
        )

    except Exception as exc:
        return False, f"Unable to read email secrets: {exc}"

    if not sender_email or not receiver_email or not app_password:
        return False, "Email sender, receiver, or password is empty."

    # Create email message
    msg = EmailMessage()
    msg["Subject"] = f"FIREGUARD AI ALERT: {status}"
    msg["From"] = sender_email
    msg["To"] = receiver_email

    try:
        confidence_value = float(confidence)
        if 0 <= confidence_value <= 1:
            confidence_text = f"{confidence_value:.1%}"
        else:
            confidence_text = f"{confidence_value:.2f}"

        msg.set_content(
            f"FIREGUARD AI ALERT\n\n"
            f"Status: {status}\n"
            f"Confidence: {confidence_text}\n"
            f"Risk level: {risk_level}\n"
            f"Risk score: {risk_score}\n"
            f"Location: {latitude}, {longitude}\n"
            f"Timestamp: {timestamp}\n"
        )

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
