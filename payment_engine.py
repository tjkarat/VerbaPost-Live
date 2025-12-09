import streamlit as st
import stripe
import secrets_manager
import logging

# Configure logging to console as well
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_checkout_session(product_name, amount_cents, success_url, cancel_url, metadata=None):
    st.write("--- 🔍 DEBUG: STARTING STRIPE SESSION ---")
    
    # 1. Debug Secrets Loading
    try:
        stripe_key = secrets_manager.get_secret("stripe.secret_key") or secrets_manager.get_secret("STRIPE_SECRET_KEY")
        
        if not stripe_key:
            st.error("❌ CRITICAL: Stripe Key is MISSING. Check secrets.toml or Env Vars.")
            logger.error("Stripe Key Missing")
            return None, None
        
        # Show masked key to verify it's the right one
        masked_key = f"{stripe_key[:8]}...{stripe_key[-4:]}"
        st.write(f"✅ Key Loaded: `{masked_key}`")
        
        # Set the key
        stripe.api_key = stripe_key
        
    except Exception as e:
        st.error(f"❌ Error loading secrets: {e}")
        return None, None

    # 2. Construct Payload
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

    # 3. Call Stripe API with Error Trapping
    try:
        st.write("📡 Contacting Stripe API...")
        session = stripe.checkout.Session.create(**payload)
        
        if session and session.url:
            st.write(f"✅ Session Created! ID: `{session.id}`")
            st.write(f"🔗 Redirect URL: `{session.url}`")
            return session.url, session.id
        else:
            st.error("❌ Stripe returned no URL.")
            return None, None

    except stripe.error.AuthenticationError as e:
        st.error(f"❌ Stripe Auth Error: {e}")
        st.info("💡 Hint: Your API Key might be invalid or expired.")
        return None, None
    except stripe.error.APIConnectionError as e:
        st.error(f"❌ Stripe Connection Error: {e}")
        return None, None
    except Exception as e:
        st.error(f"❌ General Stripe Error: {e}")
        return None, None

def verify_session(session_id):
    # Same logic for verification
    stripe_key = secrets_manager.get_secret("stripe.secret_key") or secrets_manager.get_secret("STRIPE_SECRET_KEY")
    if stripe_key: stripe.api_key = stripe_key
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == 'paid': return True, session
        return False, None
    except: return False, None