import streamlit as st
import stripe
import secrets_manager
import logging

# Configure Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_checkout_session(product_name, amount_cents, success_url, cancel_url, metadata=None):
    try:
        # Get Key
        stripe_key = secrets_manager.get_secret("stripe.secret_key") or secrets_manager.get_secret("STRIPE_SECRET_KEY")
        if stripe_key: 
            stripe.api_key = stripe_key.strip()
        else: 
            logger.error("Stripe Key Missing")
            return None, None

        # Build Payload
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
        
        if metadata: 
            payload['metadata'] = metadata

        session = stripe.checkout.Session.create(**payload)
        return session.url, session.id
    except Exception as e:
        logger.error(f"Stripe Session Create Error: {e}")
        return None, None

def verify_session(session_id):
    """
    Verifies the Stripe session status.
    Returns: (status_string, payer_email)
    """
    # Get Key
    stripe_key = secrets_manager.get_secret("stripe.secret_key") or secrets_manager.get_secret("STRIPE_SECRET_KEY")
    if stripe_key: 
        stripe.api_key = stripe_key.strip()
    
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        
        # --- FIX: Return String "paid" to match main.py expectation ---
        if session.payment_status == 'paid':
            # Extract email safely
            payer_email = session.customer_details.email if session.customer_details else None
            return "paid", payer_email
            
        return "failed", None
        
    except Exception as e:
        logger.error(f"Stripe Verify Error: {e}")
        return "error", None