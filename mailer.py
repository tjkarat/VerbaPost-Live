import os
import requests
import logging
import json
import smtplib
import time
from email.message import EmailMessage
import streamlit as st

# --- LOGGING SETUP ---
# Standardizing logging across all VerbaPost engines for production auditing.
logger = logging.getLogger(__name__)

# ==============================================================================
# CONFIGURATION & SECRETS MANAGEMENT
# ==============================================================================

# 1. POSTGRID (Physical Mail)
# Checks Environment first, then Streamlit Secrets.
POSTGRID_API_KEY = os.getenv("POSTGRID_API_KEY") or st.secrets.get("POSTGRID_API_KEY")

# CRITICAL FIX: Updated to official endpoint to prevent 404 in Production
# Previous incorrect URL: .../v1/letters
POSTGRID_URL = "https://api.postgrid.com/print-mail/v1/letters"

# 2. RESEND (Transactional Email)
# We retrieve the key and immediately sanitize it to prevent 400 Bad Request errors
# caused by accidental whitespace or quotes in the secrets file.
raw_resend_key = os.getenv("RESEND_API_KEY") or st.secrets.get("RESEND_API_KEY")
if raw_resend_key:
    SMTP_PASS = raw_resend_key.strip().strip("'").strip('"')
else:
    SMTP_PASS = None

# SMTP Settings
SMTP_SERVER = "smtp.resend.com"
SMTP_PORT = 465
SMTP_USER = "resend"


# ==============================================================================
# CORE FUNCTIONS
# ==============================================================================

def validate_address(addr_dict):
    """
    Performs a pre-flight check on the address dictionary before 
    sending to PostGrid to avoid unnecessary API costs.
    
    Args:
        addr_dict (dict): Dictionary containing address fields.
        
    Returns:
        tuple: (bool success, dict data_or_error)
    """
    required_fields = [
        "name", 
        "street", 
        "city", 
        "state", 
        "zip_code"
    ]
    
    # Iterate through fields to ensure data integrity
    for field in required_fields:
        if not addr_dict.get(field):
            logger.warning(f"Address validation failed: Missing {field}")
            return False, {"error": f"Missing field: {field}"}
    
    # Simulate a successful validation response structure.
    return True, addr_dict


def send_letter(pdf_bytes, addr_to, addr_from, tier="Standard", description="VerbaPost Letter"):
    """
    Primary engine for physical mail dispatch. 
    Handles PDF encoding, JSON payload construction, and PostGrid API handshakes.
    
    Args:
        pdf_bytes (bytes): The binary PDF content.
        addr_to (dict/obj): Recipient address.
        addr_from (dict/obj): Sender address.
        tier (str): Service tier (Standard, Heirloom, etc.)
        description (str): Internal note for the dashboard.
        
    Returns:
        str or False: The Letter ID (if success) or False (if failed).
    """
    # 1. Security Check
    if not POSTGRID_API_KEY:
        logger.error("POSTGRID_API_KEY missing from environment/secrets.")
        return False

    try:
        # 2. Data Normalization (Handle Objects vs Dictionaries)
        # Recipient Data
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

        # Sender Data (Optional)
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

        # 3. Payload Construction
        payload = {
            "to": recipient_data,
            "from": sender_data,
            "description": description,
            "metadata": {
                "tier": tier,
                "timestamp": str(time.time()),
                "source": "VerbaPost_Web"
            }
        }

        # 4. File Preparation (Multipart Upload)
        files = {
            "pdf": ("letter.pdf", pdf_bytes, "application/pdf")
        }

        # 5. Handshake & Dispatch
        # Using the corrected POSTGRID_URL
        response = requests.post(
            POSTGRID_URL,
            headers={"x-api-key": POSTGRID_API_KEY},
            data={"payload": json.dumps(payload)},
            files=files
        )

        # 6. Response Handling
        if response.status_code in [200, 201, 202]:
            resp_data = response.json()
            letter_id = resp_data.get("id")
            logger.info(f"Dispatch success: {letter_id}")
            return letter_id 
        else:
            # Capture exact error for debugging
            error_text = response.text if response.text else f"Status: {response.status_code}"
            logger.error(f"PostGrid Handshake Rejected: {error_text}")
            return False

    except Exception as e:
        logger.exception(f"Fatal Dispatch Engine Error: {e}")
        return False


def send_email_notification(to_email, subject, body):
    """
    Sends a summary email of campaign results using Resend SMTP.
    Used for bulk campaign reports and order confirmations.
    """
    if not SMTP_PASS:
        logger.error("RESEND_API_KEY missing. Email notification skipped.")
        return False

    try:
        # Construct Email Object
        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = "reports@verbapost.com"
        msg['To'] = to_email

        # Connect via secure port 465 (SSL)
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        
        logger.info(f"Notification emailed successfully to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Email Dispatch Failure: {str(e)}")
        return False


# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================

def get_letter_status(letter_id):
    """
    Fetches real-time tracking status for a specific ID from PostGrid.
    """
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
    """
    Diagnostic check for environment keys. 
    Useful for the Admin Console health check.
    """
    status = "Loaded" if POSTGRID_API_KEY else "Missing"
    logger.debug(f"PostGrid API Key Status: {status}")
    
    email_status = "Loaded" if SMTP_PASS else "Missing"
    logger.debug(f"Email API Key Status: {email_status}")

# End of Mailer Module