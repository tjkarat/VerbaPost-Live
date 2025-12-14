import stripe
import streamlit as st
import re
import logging
from secrets_manager import get_secret

# Configure Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = get_secret("stripe.secret_key")
BASE_URL = get_secret("BASE_URL") or "https://verbapost.streamlit.app"

def _is_valid_email(email):
    """
    Validates email format.
    Prevents 'guest' or malformed emails from being sent to Stripe.
    """
    if not email: return False
    # Check for basic x@x.xx structure
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email))

def create_checkout_session(line_items=None, user_email=None, draft_id=None, tier=None, price=None):
    if not stripe.api_key:
        st.error("⚠️ Payment Error: Stripe API key missing.")
        return None

    # Backwards compatibility for older calls
    if line_items is None and tier and price:
        line_items = [{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": f"VerbaPost - {tier} Letter"},
                "unit_amount": int(price * 100),
            },
            "quantity": 1,
        }]

    # Base Arguments
    stripe_args = {
        "payment_method_types": ['card'],
        "line_items": line_items,
        "mode": 'payment',
        "success_url": f"{BASE_URL.rstrip('/')}/?session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": f"{BASE_URL.rstrip('/')}/?session_id=cancel",
        "client_reference_id": str(draft_id),
        "metadata": {
            "draft_id": str(draft_id),
            "original_user_email": str(user_email)
        }
    }

    # LOGIC FIX: Only pre-fill email if it's valid.
    # This forces Stripe to collect the email if we don't have a good one.
    if user_email and _is_valid_email(user_email):
        stripe_args["customer_email"] = user_email

    try:
        session = stripe.checkout.Session.create(**stripe_args)
        return session.url
        
    except Exception as e:
        logger.error(f"Stripe Checkout Error: {e}", exc_info=True)
        st.error(f"Payment Gateway Error: Please try again.")
        return None

def verify_session(session_id):
    if not stripe.api_key: return None
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == 'paid':
            return {
                "paid": True,
                "email": session.customer_details.email, 
                "amount": session.amount_total / 100.0
            }
    except Exception as e:
        logger.error(f"Verify Error: {e}")
    return None