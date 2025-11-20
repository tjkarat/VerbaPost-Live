import stripe
import streamlit as st

# --- LOAD KEYS ---
try:
    stripe.api_key = st.secrets["stripe"]["secret_key"]
except Exception as e:
    pass

def create_checkout_session(product_name, amount_in_cents, return_url):
    """
    Creates a Stripe Checkout Session.
    return_url: The URL of your app (e.g., https://verbapost.streamlit.app)
    """
    try:
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
            # Stripe will append ?session_id={CHECKOUT_SESSION_ID} to this URL automatically
            success_url=f"{return_url}?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=return_url,
        )
        return session.url, session.id
    except Exception as e:
        return None, str(e)

def check_payment_status(session_id):
    """
    Verifies a session ID with Stripe to ensure it is actually paid.
    """
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == 'paid':
            return True
    except:
        pass
    return False