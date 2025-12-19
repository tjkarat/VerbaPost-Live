import os
import requests
import logging
import json
import smtplib
import time
from email.message import EmailMessage
import streamlit as st

logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
POSTGRID_API_KEY = os.getenv("POSTGRID_API_KEY") or st.secrets.get("POSTGRID_API_KEY")
# URL synced with Admin Console to prevent 404s
POSTGRID_URL = "https://api.postgrid.com/print-mail/v1/letters"

# EMAIL CONFIG
SMTP_SERVER = "smtp.resend.com"
SMTP_PORT = 465
SMTP_USER = "resend"

# CRITICAL FIX: Aggressive key sanitization
raw_resend = os.getenv("RESEND_API_KEY")
if not raw_resend and hasattr(st, "secrets"):
    raw_resend = st.secrets.get("RESEND_API_KEY")
    
SMTP_PASS = str(raw_resend).strip().replace("'", "").replace('"', "") if raw_resend else None

def validate_address(addr_dict):
    required = ["name", "street", "city", "state", "zip_code"]
    for field in required:
        if not addr_dict.get(field):
            logger.warning(f"Address validation failed: Missing {field}")
            return False, {"error": f"Missing field: {field}"}
    return True, addr_dict

def send_letter(pdf_bytes, addr_to, addr_from, tier="Standard", description="VerbaPost Letter"):
    if not POSTGRID_API_KEY:
        logger.error("POSTGRID_API_KEY missing from environment/secrets.")
        return False, "Handshake Error: API Key Missing"

    # --- TYPE SAFETY FIX: Ensure pdf_bytes is actually bytes ---
    if isinstance(pdf_bytes, str):
        pdf_bytes = pdf_bytes.encode('utf-8')
    elif isinstance(pdf_bytes, bytearray):
        pdf_bytes = bytes(pdf_bytes)
    elif not pdf_bytes:
        return False, "Error: PDF Content Empty"

    try:
        if hasattr(addr_to, 'name'):
             recipient_data = {
                "name": addr_to.name,
                "address_line1": addr_to.street,
                "address_city": addr_to.city,
                "address_state": addr_to.state,
                "address_zip": addr_to.zip_code,
                "address_country": "US"
            }
        else:
             recipient_data = addr_to 

        sender_data = None
        if addr_from:
            if hasattr(addr_from, 'name'):
                sender_data = {
                    "name": addr_from.name,
                    "address_line1": addr_from.street,
                    "address_city": addr_from.city,
                    "address_state": addr_from.state,
                    "address_zip": addr_from.zip_code,
                    "address_country": "US"
                }
            else:
                sender_data = addr_from

        payload = {
            "to": recipient_data,
            "from": sender_data,
            "description": description,
            "metadata": {
                "tier": tier,
                "timestamp": str(time.time())
            }
        }

        # IMPORTANT: When using 'files', data must be passed as a dictionary of strings (json.dumps), 
        # not a raw JSON object, for requests to handle the multipart/form-data correctly.
        files = {"pdf": ("letter.pdf", pdf_bytes, "application/pdf")}

        response = requests.post(
            POSTGRID_URL,
            headers={"x-api-key": POSTGRID_API_KEY},
            data={"payload": json.dumps(payload)},
            files=files
        )

        if response.status_code in [200, 201, 202]:
            resp_data = response.json()
            letter_id = resp_data.get("id")
            logger.info(f"Dispatch success: {letter_id}")
            return letter_id 
        else:
            error_text = response.text if response.text else f"Status: {response.status_code}"
            logger.error(f"PostGrid Handshake Rejected: {error_text}")
            return False

    except Exception as e:
        logger.exception(f"Fatal Dispatch Engine Error: {e}")
        return False

def send_email_notification(to_email, subject, body):
    if not SMTP_PASS:
        logger.error("RESEND_API_KEY missing. Email notification skipped.")
        return False

    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = "reports@verbapost.com"
        msg['To'] = to_email

        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        
        logger.info(f"Campaign results emailed successfully to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Email Dispatch Failure: {str(e)}")
        return False

def get_letter_status(letter_id):
    if not letter_id: return "Invalid ID"
    try:
        url = f"{POSTGRID_URL}/{letter_id}"
        response = requests.get(url, headers={"x-api-key": POSTGRID_API_KEY})
        if response.status_code == 200:
            return response.json().get("status", "Unknown")
        else:
            return f"API Error: {response.status_code}"
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return "Error"

def log_debug_info():
    status = "Loaded" if POSTGRID_API_KEY else "Missing"
    logger.debug(f"PostGrid API Key Status: {status}")