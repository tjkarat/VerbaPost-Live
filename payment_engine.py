import streamlit as st
import stripe
import secrets_manager
# Configure Logging (Silent in UI, visible in Console)
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

def create_checkout_session(product_name, amount_cents, success_url, cancel_url, metadata=None):
    try:
        # 1. Try standard manager
        stripe_key = secrets_manager.get_secret("stripe.secret_key") or secrets_manager.get_secret("STRIPE_SECRET_KEY")
        
        # 2. Fallback: Check Streamlit secrets directly (Fixes QA/Cloud)
        if not stripe_key:
            try:
                stripe_key = st.secrets["stripe"]["secret_key"]
            except:
                pass

        if stripe_key: 
            stripe.api_key = stripe_key
        else: 
            st.error("❌ Stripe configuration missing.")
            return None, None


def create_checkout_session(product_name, amount_cents, success_url, cancel_url, metadata=None):
    """
    Creates a Stripe Checkout Session.
    Returns: (url, session_id) or (None, None) on failure.
    """
    try:
        stripe_key = secrets_manager.get_secret("stripe.secret_key") or secrets_manager.get_secret("STRIPE_SECRET_KEY")
        if stripe_key: 
            stripe.api_key = stripe_key
        else: 
            logger.error("Missing Stripe API Key")
            return None, None

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
        
        # Safe handling of metadata
        if metadata: 
            payload['metadata'] = metadata

        session = stripe.checkout.Session.create(**payload)
        return session.url, session.id
    except Exception as e:
        # Logs to server console, NOT the user screen
        logger.error(f"Stripe Checkout Error: {e}")
        return None, None

def verify_session(session_id):
    """
    Verifies a Stripe Session ID.
    Returns: (is_paid: bool, session_object)
    """
    try:
        stripe_key = secrets_manager.get_secret("stripe.secret_key") or secrets_manager.get_secret("STRIPE_SECRET_KEY")
        if stripe_key: 
            stripe.api_key = stripe_key
        
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == 'paid': 
            return True, session
        return False, None
    except Exception as e:
        logger.error(f"Stripe Verification Error: {e}")
        return False, None