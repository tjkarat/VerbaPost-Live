import streamlit as st
import stripe
import secrets_manager

def create_checkout_session(product_name, amount_cents, success_url, cancel_url, metadata=None):
    try:
        # Get Key safely
        stripe_key = secrets_manager.get_secret("stripe.secret_key") or secrets_manager.get_secret("STRIPE_SECRET_KEY")
        
        if stripe_key:
            stripe.api_key = stripe_key
        else:
            st.error("DEBUG: Stripe Keys Missing in Secrets")
            return None, None

        session_payload = {
            'payment_method_types': ['card'],
            'automatic_tax': {'enabled': True},
            'line_items': [{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': product_name,
                    },
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

        # --- THE FIX: Accept metadata so ui_main doesn't crash ---
        if metadata:
            session_payload['metadata'] = metadata

        session = stripe.checkout.Session.create(**session_payload)
        return session.url, session.id
        
    except Exception as e:
        st.error(f"Stripe Error: {e}")
        return None, None

def verify_session(session_id):
    """
    Verifies payment with Stripe and returns the session object.
    """
    stripe_key = secrets_manager.get_secret("stripe.secret_key") or secrets_manager.get_secret("STRIPE_SECRET_KEY")
    if stripe_key:
        stripe.api_key = stripe_key
        
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == 'paid':
            return True, session
        return False, None
    except:
        return False, None