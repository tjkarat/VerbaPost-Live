import streamlit as st
import stripe

# --- 1. ROBUST KEY LOADING ---
# This tries both "secrets.stripe.secret_key" AND "STRIPE_SECRET_KEY"
try:
    if "stripe" in st.secrets:
        stripe.api_key = st.secrets["stripe"]["secret_key"]
    else:
        stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]
except Exception:
    stripe.api_key = None

def create_checkout_session(product_name, amount_cents, success_url, cancel_url):
    """
    Creates a Stripe Checkout Session.
    Returns (url, session_id) or (None, None) if failed.
    """
    if not stripe.api_key:
        print("❌ Error: Stripe API Key is missing.")
        return None, None

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': product_name,
                    },
                    'unit_amount': amount_cents,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=success_url + "&session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
        )
        return session.url, session.id
    except Exception as e:
        print(f"❌ Stripe Error: {e}")
        return None, None

def check_payment_status(session_id):
    """
    Verifies if a session was actually paid.
    """
    if not stripe.api_key: return False
    
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        return session.payment_status == 'paid'
    except Exception:
        return False