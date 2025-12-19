import os
import requests
import logging
import json
import smtplib
import time
from email.message import EmailMessage
import streamlit as st

logger = logging.getLogger(__name__)

# --- CONFIGURATION (DISCOVERY LOGIC) ---
# CRITICAL FIX: Robust secret discovery to ensure handshake with PostGrid.
# Checks Environment first, then Streamlit Secrets.
POSTGRID_API_KEY = os.getenv("POSTGRID_API_KEY") or st.secrets.get("POSTGRID_API_KEY")
# URL synced with Admin Console to prevent 404s
POSTGRID_URL = "https://api.postgrid.com/print-mail/v1/letters"

# EMAIL CONFIGURATION (RESEND/SMTP)
SMTP_SERVER = "smtp.resend.com"
SMTP_PORT = 465
SMTP_USER = "resend"

# CRITICAL FIX: Aggressive key sanitization (removes quotes/spaces)
raw_resend = os.getenv("RESEND_API_KEY") or st.secrets.get("RESEND_API_KEY")
SMTP_PASS = str(raw_resend).strip().replace("'", "").replace('"', "") if raw_resend else None

def validate_address(addr_dict):
    """
    Performs a pre-flight check on the address dictionary before 
    sending to PostGrid to avoid unnecessary API costs.
    """
    required_fields = [
        "name", 
        "street", 
        "city", 
        "state", 
        "zip_code"
    ]
    
    for field in required_fields:
        if not addr_dict.get(field):
            logger.warning(f"Address validation failed: Missing {field}")
            return False, {"error": f"Missing field: {field}"}
    
    # Simulate a successful validation response structure.
    return True, addr_dict

def send_letter(pdf_bytes, addr_to, addr_from, tier="Standard", description="VerbaPost Letter"):
    """
    Primary engine for physical mail dispatch. Handles PDF encoding, 
    JSON payload construction, and PostGrid API handshakes.
    """
    if not POSTGRID_API_KEY:
        logger.error("POSTGRID_API_KEY missing from environment/secrets.")
        return False, "Handshake Error: API Key Missing"

    try:
        # DATA UNPACKING: Ensure properties are valid strings
        # Safely handling object vs dict access
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
             recipient_data = addr_to # Assume it's already a dict if not object

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

        # Preparing the multi-part request for PostGrid.
        payload = {
            "to": recipient_data,
            "from": sender_data,
            "description": description,
            "metadata": {
                "tier": tier,
                "timestamp": str(time.time())
            }
        }

        # Multi-part file construction for PDF transmission.
        files = {
            "pdf": ("letter.pdf", pdf_bytes, "application/pdf")
        }

        # HANDSHAKE DISPATCH
        response = requests.post(
            POSTGRID_URL,
            headers={"x-api-key": POSTGRID_API_KEY},
            data={"payload": json.dumps(payload)},
            files=files
        )

        # Evaluating the response from the print service.
        if response.status_code in [200, 201, 202]:
            resp_data = response.json()
            letter_id = resp_data.get("id")
            logger.info(f"Dispatch success: {letter_id}")
            return letter_id # Return ID directly for success logic
        else:
            # RETURN EXACT REJECTION TEXT
            error_text = response.text if response.text else f"Status: {response.status_code}"
            logger.error(f"PostGrid Handshake Rejected: {error_text}")
            return False

    except Exception as e:
        logger.exception(f"Fatal Dispatch Engine Error: {e}")
        return False

def send_email_notification(to_email, subject, body):
    """
    Sends a summary email of campaign results using Resend SMTP.
    Used for bulk campaign reports.
    """
    if not SMTP_PASS:
        logger.error("RESEND_API_KEY missing. Email notification skipped.")
        return False

    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = "reports@verbapost.com"
        msg['To'] = to_email

        # Connect via secure port 465.
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        
        logger.info(f"Campaign results emailed successfully to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Email Dispatch Failure: {str(e)}")
        return False

# --- UTILITY FUNCTIONS ---

def get_letter_status(letter_id):
    """Fetches tracking status for a specific ID."""
    if not letter_id:
        return "Invalid ID"
        
    try:
        url = f"{POSTGRID_URL}/{letter_id}"
        response = requests.get(
            url, 
            headers={"x-api-key": POSTGRID_API_KEY}
        )
        
        if response.status_code == 200:
            return response.json().get("status", "Unknown")
        else:
            return f"API Error: {response.status_code}"
            
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return "Error"

def log_debug_info():
    """Diagnostic check for environment keys."""
    status = "Loaded" if POSTGRID_API_KEY else "Missing"
    logger.debug(f"PostGrid API Key Status: {status}")

# End of Mailer