import stripe
import streamlit as st

# --- LOAD THE KEY ---
try:
    # FIX: Changed from ["api_key"] to ["secret_key"] to match your secrets.toml
    stripe.api_key = st.secrets["stripe"]["secret_key"]
except Exception as e:
    # If secrets are missing, we print this to the logs for debugging
    print(f"Secret loading error: {e}")
    pass

def create_checkout_session(product_name, amount_in_cents, success_url, cancel_url):
    """
    Creates a Stripe Checkout Session and returns the URL.
    """
    try:
        # Verify key exists before trying
        if not stripe.api_key:
            return "Error: Stripe API Key is missing. Check Streamlit Secrets."

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
