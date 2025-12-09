import streamlit as st
import stripe
import secrets_manager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_checkout_session(product_name, amount_cents, success_url, cancel_url, metadata=None):
    st.write("--- 🔍 DEBUG: STRIPE SESSION START ---")
    
    # 1. Fetch Key
    try:
        stripe_key = secrets_manager.get_secret("stripe.secret_key") or secrets_manager.get_secret("STRIPE_SECRET_KEY")
        if not stripe_key:
            st.error("❌ Stripe Key Missing")
            return None, None
        
        masked = f"{stripe_key[:8]}...{stripe_key[-4:]}"
        st.write(f"✅ Key Found: `{masked}`")
        stripe.api_key = stripe_key
    except Exception as e:
        st.error(f"❌ Key Error: {e}")
        return None, None

    # 2. Build Payload
    payload = {
        'payment_method_types': ['card'],
        'automatic_tax': {'enabled': True},
        'line_items': [{
            'price_data': {
                'currency': 'usd',
                'product_data': {'name': product_name},
                'unit_amount': amount_cents,
                'tax_behavior': 'exclusive', 
            },
            'quantity': 1,
        }],
        'mode': 'payment',
        'success_url': success_url,
        'cancel_url': cancel_url,
        'billing_address_collection': 'required',
    }
    
    if metadata: payload['metadata'] = metadata

    # 3. Call API
    try:
        st.write("📡 Calling Stripe API...")
        session = stripe.checkout.Session.create(**payload)
        
        if session and session.url:
            st.write(f"✅ Success! Session ID: `{session.id}`")
            st.write(f"🔗 URL: `{session.url}`")
            return session.url, session.id
        else:
            st.error("❌ Stripe returned empty URL")
            return None, None

    except Exception as e:
        st.error(f"❌ Stripe API Error: {e}")
        return None, None

def verify_session(session_id):
    stripe_key = secrets_manager.get_secret("stripe.secret_key") or secrets_manager.get_secret("STRIPE_SECRET_KEY")
    if stripe_key: stripe.api_key = stripe_key
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == 'paid': return True, session
        return False, None
    except: return False, None