import stripe
import streamlit as st

# Load the key from secrets
try:
    stripe.api_key = st.secrets["stripe"]["api_key"]
except:
    pass # Handle local dev without secrets gracefully

def create_checkout_session(product_name, amount_in_cents, success_url, cancel_url):
    """
    Creates a Stripe Checkout Session and returns the URL.
    """
    try:
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
        return session.url
    except Exception as e:
        return f"Error: {e}"
