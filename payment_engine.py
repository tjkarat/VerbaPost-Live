import streamlit as st
import stripe

def create_checkout_session(product_name, amount_cents, success_url, cancel_url):
    """
    Creates a Stripe Checkout Session and returns the URL.
    """
    try:
        # 1. Get Secret Key
        if "stripe" in st.secrets:
            stripe.api_key = st.secrets["stripe"]["sk_test_key"] # Ensure this matches your secrets.toml
        else:
            return None

        # 2. Create Session
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
        return session.url
        
    except Exception as e:
        print(f"Stripe Error: {e}")
        return None