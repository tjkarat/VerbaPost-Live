import os
import requests
import logging
import json
import smtplib
import time
from email.message import EmailMessage

# --- LOGGING SETUP ---
# Standardizing logging across all VerbaPost engines for production auditing.
logger = logging.getLogger(__name__)

# --- CONFIGURATION & ENVIRONMENT ---
# Fetching credentials from environment variables for security.
POSTGRID_API_KEY = os.getenv("POSTGRID_API_KEY")
POSTGRID_URL = "https://api.postgrid.com/v1/letters"

# EMAIL CONFIGURATION (RESEND/SMTP)
SMTP_SERVER = "smtp.resend.com"
SMTP_PORT = 465
SMTP_USER = "resend"
SMTP_PASS = os.getenv("RESEND_API_KEY")

def validate_address(addr_dict):
    """
    Performs a pre-flight check on the address dictionary before 
    sending to PostGrid to avoid unnecessary API costs.
    """
    required_fields = ["name", "street", "city", "state", "zip_code"]
    for field in required_fields:
        if not addr_dict.get(field):
            logger.warning(f"Address validation failed: Missing {field}")
            return False, {"error": f"Missing field: {field}"}
    
    # Simulate a successful validation response structure.
    return True, addr_dict

def send_letter(pdf_bytes, addr_to, addr_from, tier="Standard"):
    """
    Primary engine for physical mail dispatch. Handles PDF encoding, 
    JSON payload construction, and PostGrid API handshakes.
    """
    if not POSTGRID_API_KEY:
        logger.error("POSTGRID_API_KEY not found in environment.")
        return False, "Configuration Error: API Key Missing"

    try:
        # Construct the recipient dictionary using StandardAddress mapping.
        recipient_data = {
            "name": addr_to.name,
            "address_line1": addr_to.street,
            "address_city": addr_to.city,
            "address_state": addr_to.state,
            "address_zip": addr_to.zip_code,
            "address_country": "US"
        }

        # Construct the sender dictionary if available.
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

        # Preparing the multi-part request for PostGrid.
        payload = {
            "to": recipient_data,
            "from": sender_data,
            "description": f"VerbaPost {tier} Letter Dispatch",
            "metadata": {
                "tier": tier,
                "source": "VerbaPost Bulk Engine",
                "timestamp": str(time.time())
            }
        }

        # Multi-part file construction.
        files = {
            "pdf": ("letter.pdf", pdf_bytes, "application/pdf")
        }

        # Dispatching the request to PostGrid.
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
            logger.info(f"Letter successfully queued in PostGrid. ID: {letter_id}")
            return True, letter_id
        else:
            logger.error(f"PostGrid API Error: {response.status_code} - {response.text}")
            return False, response.text

    except Exception as e:
        logger.exception(f"Critical failure in send_letter: {str(e)}")
        return False, str(e)

def send_email_notification(to_email, subject, body):
    """
    Sends a summary email of campaign results using Resend SMTP.
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
    if not letter_id: return "Invalid"
    try:
        url = f"{POSTGRID_URL}/{letter_id}"
        response = requests.get(url, headers={"x-api-key": POSTGRID_API_KEY})
        return response.json().get("status", "Unknown") if response.status_code == 200 else "Error"
    except: return "Error"

def log_debug_info():
    """Diagnostic check for environment keys."""
    logger.debug(f"API Check: {'Loaded' if POSTGRID_API_KEY else 'Missing'}")

# End of Mailer