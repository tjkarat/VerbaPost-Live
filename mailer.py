import requests
import logging
import os
import json
import secrets_manager

logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
POSTGRID_KEY = secrets_manager.get_secret("postgrid.api_key") or secrets_manager.get_secret("POSTGRID_API_KEY")
SENDGRID_KEY = secrets_manager.get_secret("sendgrid.api_key") or secrets_manager.get_secret("SENDGRID_API_KEY")
FROM_EMAIL = secrets_manager.get_secret("admin.email") or "noreply@verbapost.com"

# --- HELPER ---
def _clean_dict(d):
    """Removes None or empty string values to satisfy strict APIs."""
    return {k: v for k, v in d.items() if v}

# --- 1. PHYSICAL MAIL (PostGrid) ---

def verify_address_data(line1, line2, city, state, zip_code, country_code="US"):
    if not POSTGRID_KEY:
        return True, {'line1': line1, 'city': city, 'state': state, 'zip': zip_code}

    # Note: Verification uses a DIFFERENT endpoint base than Print
    url = "https://api.postgrid.com/v1/add_ver/verifications"
    
    payload = _clean_dict({
        "address": _clean_dict({
            "line1": line1,
            "line2": line2,
            "city": city,
            "provinceOrState": state,
            "postalOrZip": zip_code,
            "country": country_code
        })
    })
    
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
        return True, {'line1': line1, 'city': city, 'state': state, 'zip': zip_code}

def send_letter(pdf_path, to_addr, from_addr, is_certified=False):
    """
    Uploads PDF and creates Letter in PostGrid.
    """
    if not POSTGRID_KEY:
        return False, "Missing PostGrid API Key"

    # Base URL for Print & Mail
    BASE_URL = "https://api.postgrid.com/print/v1"

    try:
        # 1. Create Contact (To)
        to_payload = _clean_dict({
            "firstName": to_addr.get('name'),
            "addressLine1": to_addr.get('address_line1'),
            "addressLine2": to_addr.get('address_line2'),
            "city": to_addr.get('address_city'),
            "provinceOrState": to_addr.get('address_state'),
            "postalOrZip": to_addr.get('address_zip'),
            "countryCode": "US"
        })
        
        logger.info(f"Creating Contact (To): {BASE_URL}/contacts")
        to_res = requests.post(f"{BASE_URL}/contacts", auth=(POSTGRID_KEY, ""), json=to_payload)
        
        if to_res.status_code not in [200, 201]: 
            logger.error(f"PostGrid Error (To): {to_res.text}")
            return False, f"Contact Error: {to_res.text}"
        to_id = to_res.json().get('id')

        # 2. Create Contact (From)
        from_payload = _clean_dict({
            "firstName": from_addr.get('name'),
            "addressLine1": from_addr.get('address_line1'),
            "addressLine2": from_addr.get('address_line2'),
            "city": from_addr.get('address_city'),
            "provinceOrState": from_addr.get('address_state'),
            "postalOrZip": from_addr.get('address_zip'),
            "countryCode": "US"
        })
        
        from_res = requests.post(f"{BASE_URL}/contacts", auth=(POSTGRID_KEY, ""), json=from_payload)
        from_id = from_res.json().get('id') if from_res.status_code in [200, 201] else None

        # 3. Create Letter
        with open(pdf_path, 'rb') as f:
            files = {'pdf': f}
            data = {
                'to': to_id,
                'from': from_id,
                'color': 'true', # Must be string 'true' in multipart/form sometimes
                'express': str(is_certified).lower(),
                'addressPlacement': 'top_first_page'
            }
            logger.info(f"Creating Letter: {BASE_URL}/letters")
            create_res = requests.post(f"{BASE_URL}/letters", auth=(POSTGRID_KEY, ""), data=data, files=files)
            
            if create_res.status_code in [200, 201]:
                return True, create_res.json()
            else:
                return False, create_res.text

    except Exception as e:
        logger.error(f"Send Letter Error: {e}")
        return False, str(e)

# --- 2. DIGITAL NOTIFICATIONS (SendGrid) ---

def send_customer_notification(user_email, notification_type, data):
    if not SENDGRID_KEY:
        logger.info(f"📧 [Mock Email] To: {user_email} | Subject: {notification_type} | Data: {data}")
        return

    subject_map = {
        "order_confirmed": "Receipt: Your VerbaPost Order",
        "letter_sent": "Success! Your letter is in the mail."
    }
    
    subject = subject_map.get(notification_type, "Notification from VerbaPost")
    
    # Simple HTML Templates
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
    else:
        html_content = f"<p>Update:</p><pre>{json.dumps(data, indent=2)}</pre>"

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
        if r.status_code not in [200, 202]:
            logger.error(f"❌ Email Failed: {r.text}")
    except Exception as e:
        logger.error(f"Email Exception: {e}")

def get_postgrid_key():
    return POSTGRID_KEY