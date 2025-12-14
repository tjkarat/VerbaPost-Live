import stripe
import streamlit as st
import re
from secrets_manager import get_secret

stripe.api_key = get_secret("stripe.secret_key")
BASE_URL = get_secret("BASE_URL") or "https://verbapost.streamlit.app"

def _is_valid_email(email):
    if not email or "@" not in email or len(email) < 5:
        return False
    return True

def create_checkout_session(line_items=None, user_email=None, draft_id=None, tier=None, price=None):
    if not stripe.api_key:
        st.error("Stripe API key missing.")
        return None

    if line_items is None and tier and price:
        line_items = [{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": f"VerbaPost - {tier} Letter"},
                "unit_amount": int(price * 100),
            },
            "quantity": 1,
        }]

    stripe_args = {
        "payment_method_types": ['card'],
        "line_items": line_items,
        "mode": 'payment',
        "success_url": f"{BASE_URL.rstrip('/')}/?session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": f"{BASE_URL.rstrip('/')}/?session_id=cancel",
        "client_reference_id": str(draft_id),
        "metadata": {"draft_id": str(draft_id), "original_user_email": str(user_email)}
    }

    # Only send email if valid and NOT "guest"
    # This ensures Stripe asks for email if we don't have a real one
    if user_email and _is_valid_email(user_email) and user_email.lower() != "guest":
        stripe_args["customer_email"] = user_email

    try:
        session = stripe.checkout.Session.create(**stripe_args)
        return session.url
    except Exception as e:
        st.error(f"Payment Error: {e}")
        return None

def verify_session(session_id):
    if not stripe.api_key: return None
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == 'paid':
            # Return captured email so we can save it for guests
            return {
                "paid": True,
                "email": session.customer_details.email, 
                "amount": session.amount_total / 100.0
            }
    except Exception as e:
        print(f"Verify Error: {e}")
    return None