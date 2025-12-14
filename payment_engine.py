import stripe
import streamlit as st
from secrets_manager import get_secret

# Initialize Stripe
stripe.api_key = get_secret("stripe.secret_key")

# Determine Base URL for redirects
BASE_URL = get_secret("BASE_URL") or "https://verbapost.streamlit.app"

def create_checkout_session(line_items=None, user_email=None, draft_id=None, tier=None, price=None):
    """
    Universal checkout function. 
    Supports modern 'line_items' (Legacy/New flow) AND older 'tier/price' arguments.
    """
    if not stripe.api_key:
        st.error("⚠️ Payment Error: Stripe API key missing.")
        return None

    # BACKWARDS COMPATIBILITY:
    # If the app calls this with old arguments (tier, price), convert them to line_items
    if line_items is None and tier and price:
        line_items = [{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": f"VerbaPost - {tier} Letter"},
                "unit_amount": int(price * 100),
            },
            "quantity": 1,
        }]

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=f"{BASE_URL.rstrip('/')}/?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{BASE_URL.rstrip('/')}/?session_id=cancel",
            customer_email=user_email,
            client_reference_id=str(draft_id),
            metadata={
                "draft_id": str(draft_id),
                "user_email": user_email
            }
        )
        return session.url
        
    except Exception as e:
        print(f"❌ Stripe Checkout Error: {e}")
        st.error(f"Payment Gateway Error: {e}")
        return None

def verify_session(session_id):
    """
    Verifies payment status on return.
    """
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
        print(f"Verify Error: {e}")
    
    return None