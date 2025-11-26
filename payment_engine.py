import streamlit as st
import stripe

def create_checkout_session(product_name, amount_cents, success_url, cancel_url):
    try:
        # Aggressive Key Loading
        if "stripe" in st.secrets:
            stripe.api_key = st.secrets["stripe"]["secret_key"]
        elif "STRIPE_SECRET_KEY" in st.secrets:
            stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]
        else:
            st.error("System Error: Stripe keys not found in secrets.")
            return None, None

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
        # Show the real error
        st.error(f"Stripe Connection Failed: {e}")
        return None, None

def check_payment_status(session_id):
    if "stripe" in st.secrets:
        stripe.api_key = st.secrets["stripe"]["secret_key"]
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        return session.payment_status == 'paid'
    except:
        return False