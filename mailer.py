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

# --- CONFIGURATION (DISCOVERY LOGIC) ---
# Check env vars first, then streamlit secrets. Ensures connection is possible.
POSTGRID_API_KEY = os.getenv("POSTGRID_API_KEY") or st.secrets.get("POSTGRID_API_KEY")
POSTGRID_URL = "https://api.postgrid.com/v1/letters"

# EMAIL CONFIG (RESEND/SMTP)
SMTP_SERVER = "smtp.resend.com"
SMTP_PORT = 465
SMTP_USER = "resend"
SMTP_PASS = os.getenv("RESEND_API_KEY") or st.secrets.get("RESEND_API_KEY")

def validate_address(addr_dict):
    """Pre-flight check for required USPS fields"""
    required = ["name", "street", "city", "state", "zip_code"]
    for field in required:
        if not addr_dict.get(field):
            return False, {"error": f"Missing {field}"}
    return True, addr_dict

def send_letter(pdf_bytes, addr_to, addr_from, tier="Standard"):
    """
    CRITICAL DISPATCH ENGINE: Unpacks StandardAddress into PostGrid JSON.
    """
    if not POSTGRID_API_KEY:
        logger.error("POSTGRID_API_KEY missing from environment.")
        return False, "API Key Missing"

    try:
        # DATA UNPACKING: Ensure PostGrid receives valid strings
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
            "description": f"VerbaPost {tier} Letter",
            "metadata": {"tier": tier, "timestamp": str(time.time())}
        }

        files = {"pdf": ("letter.pdf", pdf_bytes, "application/pdf")}

        # HANDSHAKE
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
        logger.exception(f"Fatal Dispatch Error: {e}")
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

def get_letter_status(letter_id):
    if not letter_id: return "Invalid"
    try:
        url = f"{POSTGRID_URL}/{letter_id}"
        resp = requests.get(url, headers={"x-api-key": POSTGRID_API_KEY})
        return resp.json().get("status", "Unknown") if resp.status_code == 200 else "Error"
    except: return "Error"