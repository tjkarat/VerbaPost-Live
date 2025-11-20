import stripe
import streamlit as st

# --- LOAD KEYS ---
try:
    stripe.api_key = st.secrets["stripe"]["secret_key"]
except Exception as e:
    pass

def create_checkout_session(product_name, amount_in_cents, success_url, cancel_url):
    """
    Creates a Stripe Checkout Session.
    Returns: (checkout_url, session_id)
    """
    try:
        # Verify key exists
        if not stripe.api_key:
            return None, "Error: Stripe API Key is missing."

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': product_name,
                    },
                    'unit_amount': amount_in_cents,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=success_url, 
            cancel_url=cancel_url,
        )
        # RETURN TWO VALUES (Tuple)
        return session.url, session.id
    except Exception as e:
        # RETURN TWO VALUES (None, Error Message)
        return None, str(e)

def check_payment_status(session_id):
    """
    Checks if a specific session has been paid.
    Returns: True/False
    """
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == 'paid':
            return True
    except:
        pass
    return False
