import streamlit as st
import stripe

# --- ROBUST KEY LOADING WITH DEBUGGING ---
found_key = False

# 1. Try Nested [stripe] format (What you are using)
if "stripe" in st.secrets:
    print("DEBUG: Found [stripe] section in secrets.")
    if "secret_key" in st.secrets["stripe"]:
        stripe.api_key = st.secrets["stripe"]["secret_key"]
        found_key = True
        print(f"DEBUG: Loaded nested key. Starts with: {stripe.api_key[:4]}...")
    else:
        print("DEBUG: Found [stripe] section, but 'secret_key' is missing inside it.")

# 2. Try Flat STRIPE_SECRET_KEY format (Fallback)
if not found_key and "STRIPE_SECRET_KEY" in st.secrets:
    stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]
    found_key = True
    print(f"DEBUG: Loaded flat key. Starts with: {stripe.api_key[:4]}...")

if not found_key:
    print("CRITICAL ERROR: No Stripe keys found in secrets.toml")
    stripe.api_key = None

def create_checkout_session(product_name, amount_cents, success_url, cancel_url):
    """
    Creates a Stripe Checkout Session.
    """
    if not stripe.api_key:
        print("❌ Error: Stripe API Key is None.")
        return None, None

    try:
        # Create the session
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
            success_url=success_url + "&session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
        )
        print("✅ Stripe Session Created Successfully")
        return session.url, session.id
        
    except stripe.error.AuthenticationError:
        print("❌ Stripe Auth Error: Your API Key is invalid.")
        return None, None
    except Exception as e:
        print(f"❌ Stripe General Error: {e}")
        return None, None

def check_payment_status(session_id):
    if not stripe.api_key: return False
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        return session.payment_status == 'paid'
    except Exception:
        return False