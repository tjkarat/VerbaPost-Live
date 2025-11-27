import streamlit as st
import stripe
import secrets_manager # <--- New Import

def create_checkout_session(product_name, amount_cents, success_url, cancel_url):
    try:
        # UPDATED: Get Key safely
        stripe_key = secrets_manager.get_secret("stripe.secret_key") or secrets_manager.get_secret("STRIPE_SECRET_KEY")
        
        if stripe_key:
            stripe.api_key = stripe_key
        else:
            st.error("DEBUG: Stripe Keys Missing in Secrets")
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
        st.error(f"Stripe Error: {e}")
        return None, None

def check_payment_status(session_id):
    # UPDATED: Get Key safely
    stripe_key = secrets_manager.get_secret("stripe.secret_key") or secrets_manager.get_secret("STRIPE_SECRET_KEY")
    if stripe_key:
        stripe.api_key = stripe_key
        
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        return session.payment_status == 'paid'
    except:
        return False