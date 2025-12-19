import os
import requests
import logging
import json
import smtplib
import time
from email.message import EmailMessage
import streamlit as st

# --- LOGGING SETUP ---
logger = logging.getLogger(__name__)

# --- CONFIGURATION (ROBUST KEY FINDER) ---
POSTGRID_API_KEY = os.getenv("POSTGRID_API_KEY") or st.secrets.get("POSTGRID_API_KEY")
POSTGRID_URL = "https://api.postgrid.com/v1/letters"

# EMAIL CONFIG
SMTP_SERVER = "smtp.resend.com"
SMTP_PORT = 465
SMTP_USER = "resend"
SMTP_PASS = os.getenv("RESEND_API_KEY") or st.secrets.get("RESEND_API_KEY")

def validate_address(addr_dict):
    required = ["name", "street", "city", "state", "zip_code"]
    for field in required:
        if not addr_dict.get(field):
            return False, {"error": f"Missing {field}"}
    return True, addr_dict

def send_letter(pdf_bytes, addr_to, addr_from, tier="Standard"):
    """
    HANDSHAKE ENGINE: Correctly unpacks StandardAddress strings for the API.
    """
    if not POSTGRID_API_KEY:
        logger.error("POSTGRID_API_KEY missing from system.")
        return False, "API Key Missing"

    try:
        # DATA MAPPING
        recipient_data = {
            "name": addr_to.name,
            "address_line1": addr_to.street,
            "address_city": addr_to.city,
            "address_state": addr_to.state,
            "address_zip": addr_to.zip_code,
            "address_country": "US"
        }

        sender_data = None
        if addr_from:
            sender_data = {
                "name": addr_from.name,
                "address_line1": addr_from.street,
                "address_city": addr_from.city,
                "address_state": addr_from.state,
                "address_zip": addr_from.zip_code,
                "address_country": "US"
            }

        payload = {
            "to": recipient_data,
            "from": sender_data,
            "description": f"VerbaPost {tier} Letter Dispatch",
            "metadata": {"tier": tier, "timestamp": str(time.time())}
        }

        files = {"pdf": ("letter.pdf", pdf_bytes, "application/pdf")}

        # API DISPATCH
        response = requests.post(
            POSTGRID_URL,
            headers={"x-api-key": POSTGRID_API_KEY},
            data={"payload": json.dumps(payload)},
            files=files
        )

        if response.status_code in [200, 201, 202]:
            return True, response.json().get("id")
        else:
            logger.error(f"PostGrid Reject: {response.text}")
            return False, response.text

    except Exception as e:
        logger.exception(f"Mailer Engine Failure: {e}")
        return False, str(e)

def send_email_notification(to_email, subject, body):
    if not SMTP_PASS: return False
    try:
        msg = EmailMessage()
        msg.set_content(body); msg['Subject'] = subject
        msg['From'] = "reports@verbapost.com"; msg['To'] = to_email
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASS); server.send_message(msg)
        return True
    except: return False