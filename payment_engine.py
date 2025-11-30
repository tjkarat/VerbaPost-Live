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
            # --- NEW: ENABLE AUTOMATIC TAX ---
            automatic_tax={'enabled': True},
            # ---------------------------------
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': product_name,
                    },
                    'unit_amount': amount_cents,
                    # OPTIONAL: Set tax behavior (e.g., 'exclusive' adds tax on top, 'inclusive' absorbs it)
                    'tax_behavior': 'exclusive', 
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            # We need to collect the customer's address to know their tax rate
            billing_address_collection='required',
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