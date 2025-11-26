import streamlit as st
import stripe

# --- ROBUST KEY LOADING ---
try:
    # 1. Try Nested [stripe] format (Standard TOML)
    if "stripe" in st.secrets and "secret_key" in st.secrets["stripe"]:
        stripe.api_key = st.secrets["stripe"]["secret_key"]
        
    # 2. Try Flat STRIPE_SECRET_KEY format (Env Var style)
    elif "STRIPE_SECRET_KEY" in st.secrets:
        stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]
        
    else:
        stripe.api_key = None
        print("⚠️ Stripe keys missing from secrets.")

except Exception as e:
    print(f"⚠️ Key Load Error: {e}")
    stripe.api_key = None

def create_checkout_session(product_name, amount_cents, success_url, cancel_url):
    """
    Creates a Stripe Checkout Session.
    Returns (url, session_id).
    """
    if not stripe.api_key:
        st.error("System Error: Stripe API Key is missing.")
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
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return session.url, session.id
        
    except Exception as e:
        st.error(f"Stripe Connection Error: {e}")
        return None, None

def check_payment_status(session_id):
    if not stripe.api_key: return False
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        return session.payment_status == 'paid'
    except Exception:
        return False