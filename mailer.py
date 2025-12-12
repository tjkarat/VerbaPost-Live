import requests
import logging
import os
import json
import secrets_manager

logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
# We try to fetch keys for both PostGrid (Physical) and SendGrid (Digital)
POSTGRID_KEY = secrets_manager.get_secret("postgrid.api_key") or secrets_manager.get_secret("POSTGRID_API_KEY")
SENDGRID_KEY = secrets_manager.get_secret("sendgrid.api_key") or secrets_manager.get_secret("SENDGRID_API_KEY")
FROM_EMAIL = secrets_manager.get_secret("admin.email") or "noreply@verbapost.com"

# --- 1. PHYSICAL MAIL (PostGrid) ---

def verify_address_data(line1, line2, city, state, zip_code, country_code="US"):
    """
    Validates address with PostGrid/USPS CASS.
    Returns: (is_valid, corrected_data)
    """
    if not POSTGRID_KEY:
        logger.warning("⚠️ PostGrid Key missing. Skipping verification.")
        return True, {'line1': line1, 'city': city, 'state': state, 'zip': zip_code}

    url = "https://api.postgrid.com/v1/add_ver/verifications"
    payload = {
        "address": {
            "line1": line1,
            "line2": line2,
            "city": city,
            "provinceOrState": state,
            "postalOrZip": zip_code,
            "country": country_code
        }
    }
    
    try:
        r = requests.post(url, auth=(POSTGRID_KEY, ""), json=payload)
        if r.status_code == 200:
            data = r.json()
            if data.get('status') == 'verified':
                res = data.get('data', {})
                return True, {
                    'line1': res.get('line1'),
                    'line2': res.get('line2'),
                    'city': res.get('city'),
                    'state': res.get('provinceOrState'),
                    'zip': res.get('postalOrZip')
                }
        return False, None
    except Exception as e:
        logger.error(f"Address Verification Failed: {e}")
        # Fail open (allow user to proceed even if API fails)
        return True, {'line1': line1, 'city': city, 'state': state, 'zip': zip_code}

def send_letter(pdf_path, to_addr, from_addr, is_certified=False):
    """
    Uploads PDF and creates Letter in PostGrid.
    """
    if not POSTGRID_KEY:
        return False, "Missing PostGrid API Key"

    try:
        # 1. Create Contact (To)
        to_res = requests.post("https://api.postgrid.com/print/v1/contacts", auth=(POSTGRID_KEY, ""), json={
            "firstName": to_addr.get('name'),
            "addressLine1": to_addr.get('address_line1'),
            "addressLine2": to_addr.get('address_line2'),
            "city": to_addr.get('address_city'),
            "provinceOrState": to_addr.get('address_state'),
            "postalOrZip": to_addr.get('address_zip'),
            "countryCode": "US"
        })
        if to_res.status_code not in [200, 201]: return False, f"Contact Error: {to_res.text}"
        to_id = to_res.json().get('id')

        # 2. Create Contact (From)
        from_res = requests.post("https://api.postgrid.com/print/v1/contacts", auth=(POSTGRID_KEY, ""), json={
            "firstName": from_addr.get('name'),
            "addressLine1": from_addr.get('address_line1'),
            "addressLine2": from_addr.get('address_line2'),
            "city": from_addr.get('address_city'),
            "provinceOrState": from_addr.get('address_state'),
            "postalOrZip": from_addr.get('address_zip'),
            "countryCode": "US"
        })
        from_id = from_res.json().get('id') if from_res.status_code in [200, 201] else None

        # 3. Create Letter
        with open(pdf_path, 'rb') as f:
            files = {'pdf': f}
            data = {
                'to': to_id,
                'from': from_id,
                'color': True,
                'express': is_certified,
                'addressPlacement': 'top_first_page'
            }
            create_res = requests.post("https://api.postgrid.com/print/v1/letters", auth=(POSTGRID_KEY, ""), data=data, files=files)
            
            if create_res.status_code in [200, 201]:
                return True, create_res.json()
            else:
                return False, create_res.text

    except Exception as e:
        logger.error(f"Send Letter Error: {e}")
        return False, str(e)

# --- 2. DIGITAL NOTIFICATIONS (SendGrid) ---

def send_customer_notification(user_email, notification_type, data):
    """
    Sends transactional emails via SendGrid.
    Types: 'order_confirmed', 'letter_sent'
    """
    if not SENDGRID_KEY:
        logger.info(f"📧 [Mock Email] To: {user_email} | Subject: {notification_type} | Data: {data}")
        return

    subject_map = {
        "order_confirmed": "Receipt: Your VerbaPost Order",
        "letter_sent": "Success! Your letter is in the mail."
    }
    
    subject = subject_map.get(notification_type, "Notification from VerbaPost")
    
    # Simple HTML Templates
    html_content = f"<p>Hello,</p><p>Update regarding your order:</p><pre>{json.dumps(data, indent=2)}</pre>"
    
    if notification_type == "order_confirmed":
        html_content = f"""
        <h2>Order Confirmed! 📮</h2>
        <p>Thanks for using VerbaPost. You have purchased the <b>{data.get('tier')}</b> package.</p>
        <p><b>Amount:</b> ${data.get('amount')}</p>
        <p>Please return to the app to finish recording and sending your letter.</p>
        """
    elif notification_type == "letter_sent":
        html_content = f"""
        <h2>It's on the way! 🚀</h2>
        <p>We have successfully dispatched your letter to:</p>
        <p><b>{data.get('recipient')}</b></p>
        <p>Estimated Delivery: 4-6 Business Days.</p>
        """

    url = "https://api.sendgrid.com/v3/mail/send"
    headers = {"Authorization": f"Bearer {SENDGRID_KEY}", "Content-Type": "application/json"}
    payload = {
        "personalizations": [{"to": [{"email": user_email}]}],
        "from": {"email": FROM_EMAIL},
        "subject": subject,
        "content": [{"type": "text/html", "value": html_content}]
    }
    
    try:
        r = requests.post(url, headers=headers, json=payload)
        if r.status_code in [200, 202]:
            logger.info(f"✅ Email sent to {user_email}")
        else:
            logger.error(f"❌ Email Failed: {r.text}")
    except Exception as e:
        logger.error(f"Email Exception: {e}")

def get_postgrid_key():
    return POSTGRID_KEY