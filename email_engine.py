import streamlit as st
import resend
import logging

logger = logging.getLogger(__name__)

# Initialize Resend
try:
    # Looks for [resend] api_key or [email] password in secrets
    api_key = None
    if "resend" in st.secrets:
        api_key = st.secrets["resend"]["api_key"]
    elif "email" in st.secrets:
        api_key = st.secrets["email"]["password"] # Legacy secret name
        
    if api_key:
        resend.api_key = api_key
except Exception as e:
    logger.error(f"Resend Init Error: {e}")

def send_confirmation(to_email, tracking_number, tier="Standard", order_id=None):
    """
    Sends a transaction receipt with the Certified Mail tracking number.
    """
    if not resend.api_key:
        logger.warning("No Email API Key found. Skipping notification.")
        return False

    subject = f"VerbaPost Confirmation: {tier} Letter Sent"
    
    # Dynamic text based on tracking
    tracking_html = ""
    if tracking_number:
        tracking_html = f"""
        <div style="background: #f4f4f4; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <strong>Certified Tracking Number:</strong><br>
            <span style="font-family: monospace; font-size: 18px; color: #d93025;">{tracking_number}</span>
            <br><br>
            <a href="https://tools.usps.com/go/TrackConfirmAction?tLabels={tracking_number}">Track on USPS.com</a>
        </div>
        """
    else:
        tracking_html = f"<p><strong>Order ID:</strong> {order_id}</p>"

    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #333;">Letter Dispatched 📮</h2>
        <p>Your <strong>{tier}</strong> letter has been securely transmitted to our print facility.</p>
        
        {tracking_html}
        
        <p><strong>Next Steps:</strong></p>
        <ul>
            <li>Printed on archival paper</li>
            <li>Enveloped and metered</li>
            <li>Handed to USPS within 24 hours</li>
        </ul>
        <hr>
        <p style="font-size: 12px; color: #888;">Thank you for using VerbaPost.</p>
    </div>
    """

    try:
        r = resend.Emails.send({
            "from": "VerbaPost <notifications@verbapost.com>", # Update if you have a custom domain
            "to": to_email,
            "subject": subject,
            "html": html_content
        })
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False
