import streamlit as st
from streamlit_drawable_canvas import st_canvas
import os
import tempfile
import json
import base64
import numpy as np
from PIL import Image
import io
import time
import logging
import hashlib

# --- 1. ROBUST UI IMPORTS ---
try: import ui_splash
except ImportError: ui_splash = None

try: import ui_login
except ImportError: ui_login = None

try: import ui_admin
except ImportError: ui_admin = None

try: import ui_legal
except ImportError: ui_legal = None

try: import ui_help
except ImportError: ui_help = None

try: import ui_onboarding
except ImportError: ui_onboarding = None

# --- 2. HELPER IMPORTS ---
try: import database
except ImportError: database = None

try: import ai_engine
except ImportError: ai_engine = None

try: import payment_engine
except ImportError: payment_engine = None

try: import letter_format
except ImportError: letter_format = None

try: import mailer
except ImportError: mailer = None

try: import analytics
except ImportError: analytics = None

try: import promo_engine
except ImportError: promo_engine = None

try: import secrets_manager
except ImportError: secrets_manager = None

try: import civic_engine
except ImportError: civic_engine = None

try: import bulk_engine
except ImportError: bulk_engine = None

try: import audit_engine 
except ImportError: audit_engine = None

try: import auth_engine
except ImportError: auth_engine = None

try: import pricing_engine 
except ImportError: pricing_engine = None

# --- 3. CONFIGURATION ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_URL = "https://verbapost.streamlit.app/"
YOUR_APP_URL = DEFAULT_URL

try:
    if secrets_manager:
        found_url = secrets_manager.get_secret("BASE_URL")
        if found_url: 
            YOUR_APP_URL = found_url.rstrip("/")
except: 
    pass

COUNTRIES = {
    "US": "United States", 
    "CA": "Canada", 
    "GB": "United Kingdom", 
    "FR": "France", 
    "DE": "Germany", 
    "IT": "Italy", 
    "ES": "Spain", 
    "AU": "Australia", 
    "MX": "Mexico", 
    "JP": "Japan", 
    "BR": "Brazil", 
    "IN": "India"
}

# --- 4. HELPER FUNCTIONS ---

def inject_mobile_styles():
    """
    Mobile-first CSS Enhancements to ensure buttons and inputs are usable on phones.
    """
    st.markdown("""
    <style>
        /* Mobile Input Fixes */
        @media (max-width: 768px) {
            .stTextInput input { font-size: 16px !important; } /* Prevents iOS zoom */
            .stButton button { width: 100% !important; padding: 12px !important; }
            div[data-testid="stExpander"] { width: 100% !important; }
        }
        
        /* Force white text in Hero components */
        .custom-hero, .custom-hero *, 
        .price-card, .price-card * {
            color: #FFFFFF !important;
        }
    </style>
    """, unsafe_allow_html=True)

def _render_hero(title, subtitle):
    """
    Renders the blue gradient header at the top of pages.
    """
    st.markdown(f"""
    <div class="custom-hero" style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); padding: 30px 20px; border-radius: 15px; text-align: center; margin-bottom: 25px; box-shadow: 0 8px 16px rgba(0,0,0,0.1); max-width: 100%; box-sizing: border-box;">
        <h1 style="margin: 0; font-size: clamp(1.8rem, 5vw, 3rem); font-weight: 700; line-height: 1.1; text-shadow: 0 2px 4px rgba(0,0,0,0.3);">{title}</h1>
        <div style="font-size: clamp(0.9rem, 3vw, 1.2rem); opacity: 0.95; margin-top: 8px;">{subtitle}</div>
    </div>""", unsafe_allow_html=True)

def _get_user_profile_defaults(email):
    """
    Fetches the user's saved profile address to auto-populate the 'From' fields.
    """
    if not database: 
        return {}
    
    try:
        user = database.get_user(email)
        if user:
            return {
                "w_from_name": user.full_name or "",
                "w_from_street": user.address_line1 or "",
                "w_from_street2": user.address_line2 or "",
                "w_from_city": user.address_city or "",
                "w_from_state": user.address_state or "",
                "w_from_zip": user.address_zip or "",
                "w_from_country": user.address_country or "US"
            }
    except Exception as e:
        logger.warning(f"Could not fetch profile defaults: {e}")
    return {}

def _save_addresses_to_state(tier):
    """
    Saves the address form inputs into session_state and the database draft.
    """
    u = st.session_state.get("user_email")
    
    # 1. Construct the 'From' Address Object
    if tier == "Santa": 
        st.session_state.from_addr = {
            "name": "Santa Claus", 
            "street": "123 Elf Road", 
            "city": "North Pole", 
            "state": "NP", 
            "zip": "88888", 
            "country": "NP"
        }
    else:
        st.session_state.from_addr = {
            "name": st.session_state.get("w_from_name"), 
            "street": st.session_state.get("w_from_street"),
            "address_line2": st.session_state.get("w_from_street2"), 
            "city": st.session_state.get("w_from_city"),
            "state": st.session_state.get("w_from_state"), 
            "zip": st.session_state.get("w_from_zip"), 
            "country": "US", 
            "email": u
        }

    # 2. Construct the 'To' Address Object
    if tier == "Civic":
        # Placeholder for Civic; actual targets are resolved later
        st.session_state.to_addr = {
            "name": "Civic Action", 
            "street": "Capitol", 
            "city": "DC", 
            "state": "DC", 
            "zip": "20000", 
            "country": "US"
        }
    else:
        st.session_state.to_addr = {
            "name": st.session_state.get("w_to_name"), 
            "street": st.session_state.get("w_to_street"),
            "address_line2": st.session_state.get("w_to_street2"), 
            "city": st.session_state.get("w_to_city"),
            "state": st.session_state.get("w_to_state"), 
            "zip": st.session_state.get("w_to_zip"),
            "country": st.session_state.get("w_to_country", "US")
        }
    
    # 3. Save Recipient to Address Book (if option checked)
    should_save = st.session_state.get("save_contact_opt", True)
    if should_save and database and tier != "Civic" and st.session_state.get("w_to_name"):
        try:
            database.add_contact(
                u, 
                st.session_state.w_to_name, 
                st.session_state.w_to_street, 
                st.session_state.w_to_street2, 
                st.session_state.w_to_city, 
                st.session_state.w_to_state, 
                st.session_state.w_to_zip
            )
        except Exception: 
            pass

    # 4. Update the current Draft in Database
    d_id = st.session_state.get("current_draft_id")
    if d_id and database: 
        database.update_draft_data(d_id, st.session_state.to_addr, st.session_state.from_addr)

def _render_address_book_selector(u_email):
    """
    Renders the dropdown to pick a contact from the address book.
    """
    if not database: 
        return
    
    contacts = database.get_contacts(u_email)
    if contacts:
        contact_names = ["-- Quick Fill from Address Book --"] + [c.name for c in contacts]
        
        def on_contact_change():
            selected = st.session_state.get("addr_book_sel")
            if selected and selected != "-- Quick Fill from Address Book --":
                match = next((c for c in contacts if c.name == selected), None)
                if match:
                    st.session_state.w_to_name = match.name
                    st.session_state.w_to_street = match.street
                    st.session_state.w_to_street2 = match.street2 or ""
                    st.session_state.w_to_city = match.city
                    st.session_state.w_to_state = match.state
                    st.session_state.w_to_zip = match.zip_code
                    st.session_state.w_to_country = match.country

        st.selectbox("📒 Address Book", contact_names, key="addr_book_sel", on_change=on_contact_change)

def _render_address_form(tier, is_intl):
    """
    Renders the input fields for addressing.
    Handles auto-population and layout.
    """
    # Auto-populate Return Address if empty
    if not st.session_state.get("w_from_name"):
        defaults = _get_user_profile_defaults(st.session_state.get("user_email"))
        if defaults:
            for k, v in defaults.items():
                if v: st.session_state[k] = v

    # Using st.form ensures browser autofill works correctly
    with st.form("addressing_form"):
        
        # 1. FROM ADDRESS
        st.markdown("### 🏠 Return Address")
        if tier == "Santa": 
            st.info("🎅 Sender: Santa Claus (North Pole)")
        else:
            c1, c2 = st.columns(2)
            with c1:
                st.text_input("Name", key="w_from_name", placeholder="Your Name")
                st.text_input("Street", key="w_from_street", placeholder="123 Main St")
            with c2:
                st.text_input("City", key="w_from_city", placeholder="City")
                st.text_input("State", key="w_from_state", placeholder="State")
                st.text_input("Zip", key="w_from_zip", placeholder="Zip")
            st.session_state.w_from_country = "US"

        st.markdown("---")

        # 2. TO ADDRESS
        st.markdown("### 📨 Recipient")
        if tier == "Civic":
            st.info("🏛️ **Destination: Your Representatives**")
            st.caption("We use your Return Zip Code to find officials automatically.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                st.text_input("Recipient Name", key="w_to_name", placeholder="Grandma")
                st.text_input("Recipient Street", key="w_to_street", placeholder="456 Maple Ave")
            with c2:
                if is_intl:
                    st.selectbox("Country", list(COUNTRIES.keys()), key="w_to_country")
                    st.text_input("City", key="w_to_city")
                    st.text_input("State/Prov", key="w_to_state")
                    st.text_input("Postal Code", key="w_to_zip")
                else:
                    st.text_input("Recipient City", key="w_to_city")
                    st.text_input("Recipient State", key="w_to_state")
                    st.text_input("Recipient Zip", key="w_to_zip")
                    st.session_state.w_to_country = "US"
            
            st.checkbox("Save to Address Book", key="save_contact_opt", value=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Form Submit Button
        if st.form_submit_button("✅ Save Addresses", type="primary"):
            _save_addresses_to_state(tier)
            st.toast("Addresses Saved!")

def _process_sending_logic(tier):
    """
    Handles the final 'Send' action.
    - Generates PDF
    - Handles Manual (Heirloom) vs Auto (PostGrid)
    - Updates Database
    """
    # 1. Idempotency Check (Prevent double clicks)
    draft_id = st.session_state.get("current_draft_id", "0")
    idemp_key = hashlib.sha256(f"{draft_id}_{tier}_{len(st.session_state.transcribed_text)}".encode()).hexdigest()
    
    if st.session_state.get("last_send_hash") == idemp_key:
        st.warning("⚠️ This letter has already been queued for sending.")
        return

    # 2. Validation
    to_check = st.session_state.get("to_addr", {})
    if tier != "Campaign" and tier != "Civic":
        if not to_check.get("city") or not to_check.get("zip"):
            st.error("❌ Recipient Address Incomplete! Please go back to the Addressing tab.")
            return

    # 3. Determine Targets
    targets = []
    if tier == "Campaign": 
        targets = st.session_state.get("bulk_targets", [])
    elif tier == "Civic": 
        for r in st.session_state.get("civic_targets", []):
            if r.get('address_obj'): targets.append(r['address_obj'])
    else: 
        targets.append(st.session_state.to_addr)
    
    if not targets: 
        st.error("No recipients found.")
        return

    # 4. Processing Loop
    with st.spinner("Processing Order..."):
        # UI Feedback based on Tier
        if tier in ["Heirloom", "Santa"]:
            msg = """
            <h3 style="margin:0; color: #d35400;">🏺 Preparing Hand-Crafted Letter</h3>
            <p>✓ Generating High-Res Proof...</p>
            <p>✓ Routing to Artisan Fulfillment Queue...</p>
            """
        else:
            msg = """
            <h3 style="margin:0; color: #2a5298;">📮 Preparing Your Letter</h3>
            <p>✓ Generating PDF...</p>
            <p>✓ Uploading to print facility...</p>
            """
            
        st.markdown(f"""
        <div style="text-align: center; padding: 20px; background-color: #f0f2f6; border-radius: 10px; margin-bottom: 20px;">
            {msg}
        </div>
        """, unsafe_allow_html=True)

        errs = []
        for tgt in targets:
            if not tgt.get('city'): continue 
            
            # Format Address Strings for PDF
            def _fmt(d): return f"{d.get('name','')}\n{d.get('street','')}\n{d.get('city','')}, {d.get('state','')} {d.get('zip','')}"
            to_s = _fmt(tgt)
            from_s = _fmt(st.session_state.from_addr)
            
            # Handle Signature
            sig_path = None
            if st.session_state.get("sig_data") is not None:
                img = Image.fromarray(st.session_state.sig_data.astype('uint8'), 'RGBA')
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp: 
                    img.save(tmp.name)
                    sig_path = tmp.name
            
            # Generate PDF
            pdf = letter_format.create_pdf(
                st.session_state.transcribed_text, 
                to_s, 
                from_s, 
                (tier=="Heirloom"), 
                (tier=="Santa"), 
                sig_path
            )
            
            # Cleanup Sig
            if sig_path: 
                try: os.remove(sig_path)
                except: pass

            is_ok = False
            final_status = "Failed"
            
            # --- BRANCH A: MANUAL FULFILLMENT (Heirloom/Santa) ---
            if tier in ["Heirloom", "Santa"]:
                # These orders are saved to DB but NOT sent to PostGrid automatically
                # They are flagged for human review/printing
                time.sleep(1.5) # UX Pause
                is_ok = True
                final_status = "Manual Queue"
            
            # --- BRANCH B: AUTOMATED (Standard/Civic) ---
            elif mailer:
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tpdf:
                        tpdf.write(pdf)
                        tpath = tpdf.name
                    
                    # Prepare PostGrid Objects
                    pg_to = {
                        'name': tgt.get('name'), 
                        'line1': tgt.get('street'), 
                        'line2': tgt.get('address_line2', ''), 
                        'city': tgt.get('city'), 
                        'state': tgt.get('state'), 
                        'zip': tgt.get('zip'), 
                        'country': 'US'
                    }
                    pg_from = {
                        'name': st.session_state.from_addr.get('name'), 
                        'line1': st.session_state.from_addr.get('street'), 
                        'line2': st.session_state.from_addr.get('address_line2', ''), 
                        'city': st.session_state.from_addr.get('city'), 
                        'state': st.session_state.from_addr.get('state'), 
                        'zip': st.session_state.from_addr.get('zip'), 
                        'country': 'US'
                    }

                    send_ok, send_res = mailer.send_letter(
                        tpath, 
                        pg_to, 
                        pg_from, 
                        description=f"VerbaPost {tier}",
                        is_certified=st.session_state.get("is_certified", False)
                    )
                    
                    if send_ok: 
                        is_ok = True
                        final_status = "Completed"
                    else: 
                        errs.append(f"Failed to send to {tgt.get('name')}: {send_res}")
                        final_status = "Failed"
                
                except Exception as e: 
                    errs.append(f"Mailer Exception: {str(e)}")
                    final_status = "Failed"
                finally:
                    if os.path.exists(tpath): os.remove(tpath)
            else:
                final_status = "Failed"
                errs.append("Mailer module missing")

            # Update Database Record
            if database:
                database.save_draft(
                    st.session_state.user_email, 
                    st.session_state.transcribed_text, 
                    tier, 
                    "PAID", 
                    tgt, 
                    st.session_state.from_addr, 
                    final_status
                )

        # 5. Final Result
        if not errs:
            st.success("✅ Request Received Successfully!")
            st.session_state.last_send_hash = idemp_key
            st.session_state.letter_sent_success = True
            
            # Tracking
            if analytics: 
                analytics.track_event(
                    st.session_state.get("user_email"), 
                    "letter_sent", 
                    {"count": len(targets), "tier": tier}
                )
            
            st.rerun()
        else: 
            st.error("Errors occurred during processing:")
            for e in errs:
                st.write(f"- {e}")

def reset_app(full_logout=False):
    """
    Clears session state to start a new letter.
    """
    st.query_params.clear()
    u_email = st.session_state.get("user_email")
    
    keys_to_clear = [
        "audio_path", "transcribed_text", "payment_complete", "sig_data", 
        "to_addr", "civic_targets", "bulk_targets", "bulk_paid_qty", 
        "is_intl", "is_certified", "letter_sent_success", "locked_tier", 
        "w_to_name", "w_to_street", "w_to_street2", "w_to_city", 
        "w_to_state", "w_to_zip", "w_to_country", "addr_book_idx", 
        "last_tracking_num", "campaign_errors", "current_stripe_id", 
        "current_draft_id", "pending_stripe_url", "last_selected_contact", 
        "addr_book_sel", "save_contact_opt", "last_send_hash", 
        "tracked_payment_success", "tutorial_completed", "show_tutorial", 
        "tutorial_step", "temp_user_addr", "temp_rec_addr", "show_address_fix"
    ]
    
    for k in keys_to_clear: 
        if k in st.session_state: del st.session_state[k]
        
    st.session_state.to_addr = {}
    
    if full_logout:
        if "user_email" in st.session_state: del st.session_state.user_email
        st.session_state.app_mode = "splash"
    else:
        if u_email: st.session_state.app_mode = "store"
        else: st.session_state.app_mode = "splash"

def render_sidebar():
    """
    Renders the sidebar navigation.
    """
    with st.sidebar:
        st.markdown("<div style='text-align: center; margin-bottom: 20px;'><h1>📮<br>VerbaPost</h1></div>", unsafe_allow_html=True)
        st.markdown("---")
        
        if st.session_state.get("authenticated"):
            u_email = st.session_state.get("user_email", "User")
            st.info(f"👤 {u_email}")
            if st.button("Log Out", use_container_width=True):
                st.session_state.clear()
                st.rerun()
        else:
            st.info("👤 Guest User")
            if st.button("🔑 Log In / Sign Up", type="primary", use_container_width=True):
                st.session_state.app_mode = "login"
                st.session_state.auth_view = "login"
                st.rerun()
        
        # Admin Link (Hidden for non-admins)
        try:
            admin_email = st.secrets.get("admin", {}).get("email", "").strip().lower()
            current_email = st.session_state.get("user_email", "").strip().lower()
            
            if st.session_state.get("authenticated") and current_email == admin_email and admin_email != "":
                st.write("")
                st.write("")
                st.markdown("---")
                with st.expander("🛡️ Admin Console"):
                     if st.button("Open Dashboard", use_container_width=True):
                         st.session_state.app_mode = "admin"
                         st.rerun()
        except: 
            pass
            
        st.markdown("---")
        st.caption("v3.3.1 (Full Stable)")

def render_store_page():
    if ui_onboarding: ui_onboarding.show_contextual_help("store")
    global YOUR_APP_URL
    u_email = st.session_state.get("user_email", "")
    
    if not u_email:
        st.warning("⚠️ Session Expired. Please log in to continue.")
        if st.button("Go to Login"):
            st.session_state.app_mode = "login"
            st.rerun()
        return

    _render_hero("Select Service", "Choose your letter type")
    
    c1, c2 = st.columns([2, 1])
    
    with c1:
        with st.container(border=True):
            st.subheader("Available Packages")
            
            tier_labels = {
                "Standard": "⚡ Standard ($2.99)", 
                "Heirloom": "🏺 Heirloom ($5.99)", 
                "Civic": "🏛️ Civic ($6.99)", 
                "Santa": "🎅 Santa ($9.99)", 
                "Campaign": "📢 Campaign (Bulk)"
            }
            
            tier_desc = {
                "Standard": "Professional print on standard paper. Mailed USPS First Class.", 
                "Heirloom": "Heavyweight archival stock with wet-ink style font.", 
                "Civic": "We identify your local reps and mail them physical letters.", 
                "Santa": "Magical letter from North Pole, signed by Santa.", 
                "Campaign": "Upload CSV. We mail everyone at once."
            }
            
            default_idx = 0
            stored_tier = st.session_state.get("locked_tier")
            if stored_tier and stored_tier in list(tier_labels.keys()):
                default_idx = list(tier_labels.keys()).index(stored_tier)
                
            sel = st.radio("Select Tier", list(tier_labels.keys()), index=default_idx, format_func=lambda x: tier_labels[x])
            tier_code = sel
            
            st.info(tier_desc[tier_code])
            
            qty = 1
            if tier_code == "Campaign":
                qty = st.number_input("Recipients", 10, 5000, 50, 10)
                st.caption(f"Pricing: First $2.99, then $1.99/ea")
            
            is_intl = False
            is_certified = False
            if tier_code in ["Standard", "Heirloom"]:
                c_opt1, c_opt2 = st.columns(2)
                if c_opt1.checkbox("International (+$2.00)"): is_intl = True
                if c_opt2.checkbox("Certified Mail (+$12.00)"): is_certified = True
            
            st.session_state.is_intl = is_intl
            st.session_state.is_certified = is_certified

    with c2:
        with st.container(border=True):
            st.subheader("Checkout")
            discounted = False
            code = st.text_input("Promo Code")
            if promo_engine and code and promo_engine.validate_code(code): 
                discounted = True
                st.success("✅ Applied!")
            
            final_price = 0.00
            if not discounted:
                if pricing_engine: 
                    final_price = pricing_engine.calculate_total(tier_code, is_intl, is_certified, qty)
                else: 
                    final_price = 2.99 
            
            st.metric("Total", f"${final_price:.2f}")
            
            if discounted:
                if st.button("🚀 Start (Free)", type="primary", use_container_width=True):
                    _handle_draft_creation(u_email, tier_code, final_price)
                    if promo_engine: promo_engine.log_usage(code, u_email)
                    if audit_engine: audit_engine.log_event(u_email, "PROMO_USED", "FREE", {"code": code})
                    
                    st.session_state.payment_complete = True
                    st.session_state.locked_tier = tier_code
                    st.session_state.bulk_paid_qty = qty
                    st.session_state.app_mode = "workspace"
                    st.rerun()
            else:
                if "pending_stripe_url" in st.session_state:
                    url = st.session_state.pending_stripe_url
                    st.success("✅ Link Generated!")
                    st.markdown(f'<a href="{url}" target="_blank" style="text-decoration: none;"><div style="display: block; width: 100%; padding: 14px; background: linear-gradient(135deg, #28a745 0%, #218838 100%); color: white; text-align: center; border-radius: 8px; font-weight: bold; font-size: 1.1rem; margin-top: 10px;">👉 Pay Now (Opens New Tab)</div></a>', unsafe_allow_html=True)
                    if st.button("Cancel / Reset"):
                        del st.session_state.pending_stripe_url
                        st.rerun()
                else:
                    if st.button("💳 Generate Payment Link", type="primary", use_container_width=True):
                        try:
                            d_id = _handle_draft_creation(u_email, tier_code, final_price)
                            link = f"{YOUR_APP_URL}?tier={tier_code}&session_id={{CHECKOUT_SESSION_ID}}"
                            if d_id: link += f"&draft_id={d_id}"
                            if is_intl: link += "&intl=1"
                            if is_certified: link += "&certified=1"
                            if tier_code == "Campaign": link += f"&qty={qty}"
                            
                            if payment_engine:
                                with st.spinner("Generating secure payment link..."):
                                    url, sess_id = payment_engine.create_checkout_session(f"VerbaPost {tier_code}", int(final_price*100), link, YOUR_APP_URL)
                                    if url:
                                        if audit_engine: audit_engine.log_event(u_email, "CHECKOUT_STARTED", sess_id, {"tier": tier_code})
                                        st.session_state.pending_stripe_url = url
                                        st.rerun()
                                    else: st.error("⚠️ Stripe Error: Could not generate link.")
                            else: st.error("⚠️ Payment Engine Missing")
                        except Exception as e:
                            st.error(f"❌ System Crash: {str(e)}")

def _handle_draft_creation(email, tier, price):
    d_id = st.session_state.get("current_draft_id")
    success = False
    if d_id and database:
        success = database.update_draft_data(d_id, status="Draft", tier=tier, price=price)
    if not success and database:
        d_id = database.save_draft(email, "", tier, price)
        st.session_state.current_draft_id = d_id
        st.query_params["draft_id"] = str(d_id)
    return d_id

def render_address_intervention(user_input, recommended):
    """
    Shows the side-by-side comparison when address standardization makes changes.
    """
    st.warning("⚠️ We found a better match for that address.")
    
    c1, c2 = st.columns(2)
    
    # Left: What they typed
    with c1:
        st.markdown("**You Entered:**")
        st.text(f"{user_input.get('line1')}")
        if user_input.get('line2'): st.text(f"{user_input.get('line2')}")
        st.text(f"{user_input.get('city')}, {user_input.get('state')} {user_input.get('zip')}")
        
        if st.button("Use My Version (Risky)", key="btn_keep_mine"):
            st.session_state.recipient_address = user_input
            # Clear flag to proceed
            st.session_state.show_address_fix = False
            st.rerun()

    # Right: What USPS recommends
    with c2:
        st.markdown("**USPS Recommended:**")
        st.markdown(f"<div style='background-color:#e6ffe6; padding:10px; border-radius:5px; border:1px solid #b3ffb3; color:#006600;'>{recommended.get('line1')}</div>", unsafe_allow_html=True)
        if recommended.get('line2'):
            st.markdown(f"<div style='background-color:#e6ffe6; padding:10px; border-radius:5px; border:1px solid #b3ffb3; color:#006600; margin-top:2px;'>{recommended.get('line2')}</div>", unsafe_allow_html=True)
        
        st.markdown(f"<div style='background-color:#e6ffe6; padding:10px; border-radius:5px; border:1px solid #b3ffb3; color:#006600; margin-top:2px;'>{recommended.get('city')}, {recommended.get('state')} {recommended.get('zip')}</div>", unsafe_allow_html=True)
        
        if st.button("✅ Use Recommended", type="primary", key="btn_use_rec"):
            st.session_state.recipient_address = recommended
            # Update the form fields in state so they persist
            st.session_state.w_to_street = recommended.get('line1')
            st.session_state.w_to_street2 = recommended.get('line2')
            st.session_state.w_to_city = recommended.get('city')
            st.session_state.w_to_state = recommended.get('state')
            st.session_state.w_to_zip = recommended.get('zip')
            
            # Clear flag
            st.session_state.show_address_fix = False
            st.rerun()

def render_workspace_page():
    if ui_onboarding: ui_onboarding.show_contextual_help("workspace")
    _render_hero("Workspace", "Compose your letter")
    
    tier = st.session_state.get("locked_tier", "Standard")
    
    # 1. Address Verification Intercept
    if st.session_state.get("show_address_fix"):
        render_address_intervention(st.session_state.temp_user_addr, st.session_state.temp_rec_addr)
        return

    # 2. Main Tabs
    t1, t2 = st.tabs(["🏠 1. Addressing", "✍️ 2. Write / Dictate"])
    
    # --- TAB 1: ADDRESSING ---
    with t1:
        # Address Book at TOP
        _render_address_book_selector(st.session_state.get("user_email"))
        
        if tier == "Civic":
            st.info("For Civic letters, we just need your Return Address to find your representatives.")
        
        # Show Address Form
        _render_address_form(tier, st.session_state.get("is_intl", False))
        
        # Explicit verification button for "Bring Your Own Address"
        if tier not in ["Civic", "Campaign"]:
            st.write("")
            if st.button("🔍 Verify Recipient Address"):
                # Construct raw dict from current state
                raw = {
                    "line1": st.session_state.get("w_to_street"),
                    "line2": st.session_state.get("w_to_street2"),
                    "city": st.session_state.get("w_to_city"),
                    "state": st.session_state.get("w_to_state"),
                    "zip": st.session_state.get("w_to_zip"),
                    "country": "US"
                }
                
                if mailer:
                    with st.spinner("Checking with USPS..."):
                        status, clean, errs = mailer.verify_address_details(raw)
                        
                    if status in ["verified", "corrected"]:
                        # Even if just 'verified', we might want to update casing/zip+4
                        if status == "corrected":
                            st.session_state.temp_user_addr = raw
                            st.session_state.temp_rec_addr = clean
                            st.session_state.show_address_fix = True
                            st.rerun()
                        else:
                            st.success("Address is valid! ✅")
                    else:
                        st.error(f"Invalid Address: {errs}")

    # --- TAB 2: COMPOSE ---
    with t2:
        st.markdown("### Choose your input method:")
        
        # METHOD A: RECORDER
        with st.expander("🎙️ Option A: Record Voice (Recommended)", expanded=True):
            st.info("""
            **How to Record:**
            1. Click the microphone icon below.
            2. Speak your letter clearly.
            3. Click the icon again (or 'Stop') when finished.
            4. Then click **'Transcribe Recording'**.
            """)
            audio_bytes = st.audio_input("Recorder")
            if audio_bytes:
                if st.button("📝 Transcribe Recording", type="primary"):
                    if ai_engine:
                        with st.spinner("Transcribing..."):
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                                tmp.write(audio_bytes.getvalue()); tmp_path = tmp.name
                            try:
                                text = ai_engine.transcribe_audio(tmp_path)
                                st.session_state.transcribed_text = text
                                if os.path.exists(tmp_path): os.remove(tmp_path)
                                st.rerun()
                            except Exception as e: st.error(f"Error: {e}")

        # METHOD B: UPLOAD
        with st.expander("📂 Option B: Upload Audio File"):
            st.caption("Supports MP3, WAV, M4A (iPhone Voice Memos). Limit 200MB.")
            aud_file = st.file_uploader("Select File", type=["mp3", "wav", "m4a", "ogg"])
            if aud_file:
                if st.button("📝 Transcribe Uploaded File"):
                    if ai_engine:
                        with st.spinner("Transcribing..."):
                            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{aud_file.name.split('.')[-1]}") as tmp:
                                tmp.write(aud_file.getvalue()); tmp_path = tmp.name
                            try:
                                text = ai_engine.transcribe_audio(tmp_path)
                                st.session_state.transcribed_text = text
                                if os.path.exists(tmp_path): os.remove(tmp_path)
                                st.success("Done!")
                                st.rerun()
                            except Exception as e: st.error(f"Error: {e}")

        # METHOD C: TYPE
        st.markdown("---")
        st.markdown("#### ⌨️ Or Type Manually")
        
        # AI TOOLS
        c1, c2, c3, c4 = st.columns(4)
        current_text = st.session_state.get("transcribed_text", "")
        
        def _ai_fix(style):
            if ai_engine and current_text:
                with st.spinner(f"Rewriting ({style})..."): 
                    st.session_state.transcribed_text = ai_engine.refine_text(current_text, style)
                    st.rerun()
        
        if c1.button("Grammar"): _ai_fix("Grammar")
        if c2.button("Professional"): _ai_fix("Professional")
        if c3.button("Friendly"): _ai_fix("Friendly")
        if c4.button("Concise"): _ai_fix("Concise")

        # Editor
        val = st.session_state.get("transcribed_text", "")
        new_val = st.text_area("Body Text", value=val, height=300)
        if new_val != val: st.session_state.transcribed_text = new_val

    # Footer Action
    st.markdown("---")
    if st.button("➡️ Review & Send", type="primary", use_container_width=True):
        if not st.session_state.get("transcribed_text"):
            st.error("Please write or transcribe your letter first.")
        else:
            st.session_state.app_mode = "review"
            st.rerun()

def render_review_page():
    if ui_onboarding: ui_onboarding.show_contextual_help("review")
    
    _render_hero("Review", "Finalize & Send")
    if st.session_state.get("letter_sent_success"):
        st.success("✅ Letter Sent Successfully!")
        st.balloons()
        st.markdown("### Next Steps")
        if st.button("📮 Start New Letter", type="primary", use_container_width=True):
            reset_app()
            st.rerun()
        return

    if st.button("⬅️ Edit"): 
        st.session_state.app_mode = "workspace"
        st.rerun()
        
    tier = st.session_state.get("locked_tier", "Standard")
    
    # Show Final Text Read-Only
    current_text = st.session_state.get("transcribed_text", "")
    st.text_area("Final Body Text", value=current_text, height=300, disabled=True)

    st.markdown("### 📄 Letter Preview")
    
    if tier == "Civic" and st.session_state.get("civic_targets"):
        st.info("🏛️ Sending to:")
        for t in st.session_state.civic_targets:
            st.write(f"- {t['name']} ({t['title']})")
            
    if not current_text: 
        st.warning("Please enter some text before generating a preview.")
    else:
        try:
            # Generate Preview PDF
            to_s = ""; from_s = ""
            if tier == "Civic" and st.session_state.get("civic_targets"):
                first_rep = st.session_state.civic_targets[0]
                d = first_rep.get('address_obj', st.session_state.to_addr)
                to_s = f"{d.get('name','')}\n{d.get('street','')}\n{d.get('city','')}, {d.get('state','')} {d.get('zip','')}"
            elif st.session_state.get("to_addr"):
                d = st.session_state.to_addr
                to_s = f"{d.get('name','')}\n{d.get('street','')}\n{d.get('city','')}, {d.get('state','')} {d.get('zip','')}"

            if st.session_state.get("from_addr"):
                d = st.session_state.from_addr
                from_s = f"{d.get('name','')}\n{d.get('street','')}\n{d.get('city','')}, {d.get('state','')} {d.get('zip','')}"
            
            sig_path = None
            if st.session_state.get("sig_data") is not None:
                img = Image.fromarray(st.session_state.sig_data.astype('uint8'), 'RGBA')
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp: 
                    img.save(tmp.name)
                    sig_path = tmp.name
            
            if letter_format:
                pdf_bytes = letter_format.create_pdf(
                    current_text, 
                    to_s, 
                    from_s, 
                    (tier=="Heirloom"), 
                    (tier=="Santa"), 
                    sig_path
                )
                
                if pdf_bytes and len(pdf_bytes) > 100:
                    st.download_button(
                        label="⬇️ Download PDF Proof", 
                        data=pdf_bytes, 
                        file_name="letter_preview.pdf", 
                        mime="application/pdf", 
                        type="primary", 
                        use_container_width=True
                    )
                else: 
                    st.error("Failed to generate PDF content.")
            
            if sig_path: 
                try: os.remove(sig_path)
                except: pass
                
        except Exception as e: 
            st.error(f"Preview Failed: {e}")

    if st.button("🚀 Send Letter", type="primary"):
        _process_sending_logic(tier)

# --- 10. MAIN ROUTER ---
def render_main():
    inject_mobile_styles()
    
    # 1. RENDER SIDEBAR (Critical for Admin Access)
    render_sidebar()
    
    # 2. ANALYTICS
    if analytics: 
        try: analytics.inject_ga()
        except: pass
    
    # 3. ROUTING
    mode = st.session_state.get("app_mode", "splash")
    
    if mode == "splash" and ui_splash: 
        ui_splash.render_splash()
        
    elif mode == "login" and ui_login: 
        ui_login.render_login()
        
    elif mode == "store": 
        render_store_page()
        
    elif mode == "workspace": 
        render_workspace_page()
        
    elif mode == "review": 
        render_review_page()
        
    elif mode == "admin" and ui_admin: 
        ui_admin.show_admin()
        
    elif mode == "legal" and ui_legal: 
        ui_legal.render_legal()
        
    elif mode == "legacy" and "ui_legacy" in globals():
        ui_legacy.render_legacy_page()
        
    else: 
        # Fallback Logic
        if st.session_state.get("authenticated"):
            st.session_state.app_mode = "store"
            render_store_page()
        else:
            st.session_state.app_mode = "splash"
            if ui_splash: ui_splash.render_splash()