import streamlit as st
import time
import os
import hashlib
from datetime import datetime
import pandas as pd
import io
import base64
import re

# --- CRITICAL IMPORTS ---
import database 

# --- ENGINE IMPORTS ---
try: import ai_engine
except ImportError: ai_engine = None
try: import payment_engine
except ImportError: payment_engine = None
try: import mailer
except ImportError: mailer = None
try: import letter_format
except ImportError: letter_format = None
try: import address_standard
except ImportError: address_standard = None
try: import pricing_engine
except ImportError: pricing_engine = None
try: import bulk_engine
except ImportError: bulk_engine = None
try: import audit_engine
except ImportError: audit_engine = None
try: import civic_engine
except ImportError: civic_engine = None
try: import promo_engine
except ImportError: promo_engine = None
try: import secrets_manager
except ImportError: secrets_manager = None

# --- UI MODULE IMPORTS ---
try: import ui_splash
except ImportError: ui_splash = None
try: import ui_login
except ImportError: ui_login = None
try: import ui_admin
except ImportError: ui_admin = None
try: import ui_legal
except ImportError: ui_legal = None
try: import ui_legacy
except ImportError: ui_legacy = None
try: import ui_heirloom
except ImportError: ui_heirloom = None


# --- HELPER: SAFE PROFILE GETTER ---
def get_profile_field(profile, field, default=""):
    if not profile: return default
    if isinstance(profile, dict): return profile.get(field, default)
    return getattr(profile, field, default)

def _ensure_profile_loaded():
    if st.session_state.get("authenticated") and not st.session_state.get("profile_synced"):
        try:
            email = st.session_state.get("user_email")
            profile = database.get_user_profile(email)
            if profile:
                st.session_state.user_profile = profile
                st.session_state.from_name = get_profile_field(profile, "full_name")
                st.session_state.from_street = get_profile_field(profile, "address_line1")
                st.session_state.from_city = get_profile_field(profile, "address_city")
                st.session_state.from_state = get_profile_field(profile, "address_state")
                st.session_state.from_zip = get_profile_field(profile, "address_zip")
                st.session_state.profile_synced = True 
                st.rerun()
        except Exception as e:
            print(f"Profile Load Error: {e}")

# --- CSS INJECTOR (SAFE FONT LOADING) ---
def inject_custom_css(text_size=16):
    import base64
    font_face_css = ""
    try:
        # Try loading the custom font file
        with open("type_right.ttf", "rb") as f:
            b64_font = base64.b64encode(f.read()).decode()
        font_face_css = f"""
            @font-face {{
                font-family: 'TypeRight';
                src: url('data:font/ttf;base64,{b64_font}') format('truetype');
            }}
        """
    except FileNotFoundError:
        # Fallback if file is missing (Prevents Crash)
        font_face_css = ""

    st.markdown(f"""
        <style>
        {font_face_css}
        .stTextArea textarea {{
            font-family: 'TypeRight', 'Courier New', Courier, monospace !important;
            font-size: {text_size}px !important;
            line-height: 1.6 !important;
            background-color: #fdfbf7; 
            color: #333;
        }}
        .stTextInput input {{ font-family: 'Helvetica Neue', sans-serif !important; }}
        p, li, .stMarkdown {{ font-family: 'Helvetica Neue', sans-serif; font-size: {text_size}px !important; line-height: 1.6 !important; }}
        .price-card {{ background-color: #ffffff; border-radius: 12px; padding: 20px 15px; text-align: center; border: 1px solid #e0e0e0; height: 220px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); display: flex; flex-direction: column; justify-content: flex-start; gap: 5px; }}
        .price-header {{ font-weight: 700; font-size: 1.4rem; color: #1f2937; margin-bottom: 2px; height: 35px; display: flex; align-items: center; justify-content: center; }}
        .price-sub {{ font-size: 0.75rem; font-weight: 600; color: #9ca3af; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 5px; }}
        .price-tag {{ font-size: 2.4rem; font-weight: 800; color: #d93025; margin: 5px 0; }}
        .price-desc {{ font-size: 0.9rem; color: #4b5563; line-height: 1.3; margin-top: auto; padding-bottom: 5px; min-height: 50px; }}
        .stTabs [data-baseweb="tab"] p {{ font-size: 1.2rem !important; font-weight: 600 !important; }}
        .stTabs [data-baseweb="tab"] {{ height: 60px; white-space: pre-wrap; background-color: #F0F2F6; border-radius: 8px 8px 0px 0px; gap: 2px; padding: 10px; border: 1px solid #ccc; border-bottom: none; color: #333; }}
        .stTabs [aria-selected="true"] {{ background-color: #FF4B4B !important; border: 1px solid #FF4B4B !important; color: white !important; }}
        .stTabs [aria-selected="true"] p {{ color: white !important; }}
        .instruction-box {{ background-color: #FEF3C7; border-left: 6px solid #F59E0B; padding: 15px; margin-bottom: 20px; border-radius: 4px; color: #000; }}
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        </style>
    """, unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---
def reset_app_state():
    keys_to_keep = ["authenticated", "user_email", "user_name", "user_role", "user_profile", "profile_synced"]
    for key in list(st.session_state.keys()):
        if key not in keys_to_keep:
            del st.session_state[key]
    if st.session_state.get("authenticated"):
        st.session_state.app_mode = "store"
    else:
        st.session_state.app_mode = "splash"
    st.rerun()

def load_address_book():
    if not st.session_state.get("authenticated"):
        return {}
    try:
        user_email = st.session_state.get("user_email")
        contacts = database.get_contacts(user_email)
        result = {}
        for c in contacts:
            name = c.get('name', '')
            city = c.get('city', 'Unknown')
            label = f"{name} ({city})"
            result[label] = c
        return result
    except Exception as e:
        print(f"Address Book Error: {e}")
        return {}

def _handle_draft_creation(email, tier, price):
    d_id = st.session_state.get("current_draft_id")
    success = False
    if d_id:
        success = database.update_draft_data(d_id, status="Draft", tier=tier, price=price)
    if not success or not d_id:
        d_id = database.save_draft(email, "", tier, price)
        st.session_state.current_draft_id = d_id
    return d_id

# --- GLOBAL CALLBACKS ---
def cb_select_tier(tier, price, user_email):
    try:
        st.query_params.clear()
        st.session_state.locked_tier = tier
        st.session_state.locked_price = price
        st.session_state.app_mode = "workspace"
        if user_email:
            _handle_draft_creation(user_email, tier, price)
    except Exception as e:
        print(f"Draft creation warning: {e}")
        st.session_state.app_mode = "workspace"

# --- PAGE RENDERERS ---

def render_store_page():
    inject_custom_css(16)
    u_email = st.session_state.get("user_email", "")
    
    if not u_email:
        st.warning("⚠️ Session Expired. Please log in to continue.")
        if st.button("Go to Login"):
            st.session_state.app_mode = "login"
            st.rerun()
        return

    with st.expander("❓ How VerbaPost Works", expanded=False):
        st.markdown("""
        1. **Select Service:** Choose your letter tier below.
        2. **Write:** Type or dictate your content.
        3. **Address:** Load or enter recipient.
        4. **Send:** We print and mail it via USPS.
        """)

    st.markdown("## 📮 Choose Your Letter Service")
    
    mode = st.radio("Mode", ["Single Letter", "Bulk Campaign"], horizontal=True, label_visibility="collapsed")
    
    if mode == "Bulk Campaign":
        st.info("📢 **Campaign Mode Active.**")
        render_campaign_uploader()
        return

    c1, c2, c3, c4 = st.columns(4)
    def html_card(title, qty_text, price, desc):
        return f"""<div class="price-card"><div class="price-header">{title}</div><div class="price-sub">{qty_text}</div><div class="price-tag">${price}</div><div class="price-desc">{desc}</div></div>"""

    with c1: st.markdown(html_card("Standard", "ONE LETTER", "2.99", "Premium paper."), unsafe_allow_html=True)
    with c2: st.markdown(html_card("Heirloom", "ONE LETTER", "5.99", "Cream paper."), unsafe_allow_html=True)
    with c3: st.markdown(html_card("Civic", "3 LETTERS", "6.99", "Find reps automatically."), unsafe_allow_html=True)
    with c4: st.markdown(html_card("Santa", "ONE LETTER", "9.99", "North Pole Postmark."), unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True) 
    b1, b2, b3, b4 = st.columns(4)
    with b1: st.button("Select Standard", use_container_width=True, on_click=cb_select_tier, args=("Standard", 2.99, u_email))
    with b2: st.button("Select Heirloom", key="btn_store_heirloom_product", use_container_width=True, on_click=cb_select_tier, args=("Heirloom", 5.99, u_email))
    with b3: st.button("Select Civic", use_container_width=True, on_click=cb_select_tier, args=("Civic", 6.99, u_email))
    with b4: st.button("Select Santa", use_container_width=True, on_click=cb_select_tier, args=("Santa", 9.99, u_email))

def render_campaign_uploader():
    st.markdown("### 📁 Upload Recipient List (CSV)")
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
    if uploaded_file:
        contacts = bulk_engine.parse_csv(uploaded_file)
        if not contacts:
            st.error("❌ Could not parse CSV.")
            return
        st.success(f"✅ Loaded {len(contacts)} recipients.")
        st.dataframe(contacts[:5])
        total = pricing_engine.calculate_total("Campaign", qty=len(contacts))
        st.metric("Total", f"${total}")
        if st.button("Proceed"):
            st.session_state.locked_tier = "Campaign"
            st.session_state.bulk_targets = contacts
            st.session_state.app_mode = "workspace"; st.rerun()

def render_workspace_page():
    _ensure_profile_loaded()
    col_slide, col_gap = st.columns([1, 2])
    with col_slide: text_size = st.slider("Text Size", 12, 24, 16)
    inject_custom_css(text_size)
    current_tier = st.session_state.get('locked_tier', 'Draft')
    st.markdown(f"## 📝 Workspace: {current_tier}")
    with st.expander("📍 Addressing", expanded=True):
        with st.form("addressing_form"):
            col_to, col_from = st.columns(2)
            with col_to:
                if current_tier == "Campaign": st.info("📬 Bulk Mode active.")
                else: st.text_input("Name", key="to_name_input")
            with col_from:
                st.text_input("From Name", key="from_name")
                st.text_input("From Street", key="from_street")
            if st.form_submit_button("💾 Save"):
                st.session_state.addr_from = {"name": st.session_state.from_name, "street": st.session_state.from_street, "city": st.session_state.get("from_city", ""), "state": st.session_state.get("from_state", ""), "zip_code": st.session_state.get("from_zip", "")}
                st.success("✅ Saved!")
    st.divider()
    st.markdown("## ✍️ Write Letter")
    new_text = st.text_area("Body", value=st.session_state.get("letter_body", ""), height=400)
    st.session_state.letter_body = new_text
    if st.button("👀 Review & Pay (Next Step)", type="primary", use_container_width=True):
        st.session_state.app_mode = "review"; st.rerun()

def render_review_page():
    """FIXED LOGIC: Persistent placeholders for real-time progress."""
    st.markdown("## 👁️ Step 4: Secure & Send")
    current_tier = st.session_state.get("locked_tier", "Standard")
    
    # LOCK: PAYMENT STATE PERSISTENCE
    if st.query_params.get("success") == "true":
        st.session_state.campaign_paid = True

    # --- RESTORED PROMO CODE LOGIC ---
    discount = 0.0
    promo_code = st.text_input("🎟️ Promo Code (Optional)")
    if promo_code and promo_engine:
        valid, val = promo_engine.validate_promo(promo_code)
        if valid:
            discount = val
            st.success(f"✅ Coupon applied: ${discount} off")
        else:
            st.error("❌ Invalid Code")

    if current_tier == "Campaign":
        targets = st.session_state.get("bulk_targets", [])
        st.info(f"📋 Campaign Mode: Mailing {len(targets)} personalized letters.")
        
        # 1. THE PAYMENT PHASE
        if not st.session_state.get("campaign_paid"):
            st.warning("⚠️ Secure payment required to start dispatch.")
            
            raw_total = pricing_engine.calculate_total(current_tier, qty=len(targets))
            final_total = max(0.0, raw_total - discount)
            st.markdown(f"### Total: ${final_total:.2f}")
            
            if st.button("💳 Proceed to Checkout", type="primary", use_container_width=True):
                url = payment_engine.create_checkout_session(
                    line_items=[{"price_data": {"currency": "usd", "product_data": {"name": "Campaign"}, "unit_amount": int(final_total * 100)}, "quantity": 1}], 
                    user_email=st.session_state.get("user_email")
                )
                if url: st.link_button("👉 Open Payment Gateway", url)
        
        # 2. THE DISPATCH PHASE (UNLOCKED)
        else:
            st.success("✅ Payment Verified. Engine Unlocked.")
            metrics_spot = st.empty()
            progress_spot = st.empty()
            
            if "campaign_metrics" not in st.session_state:
                st.session_state.campaign_metrics = {"sent": 0, "failed": 0, "total": len(targets)}
            
            with metrics_spot.container():
                c1, c2, c3 = st.columns(3)
                c1.metric("Target", len(targets))
                c2.metric("Success ✅", st.session_state.campaign_metrics["sent"])
                c3.metric("Failed ❌", st.session_state.campaign_metrics["failed"])

            if st.button("🚀 EXECUTE CAMPAIGN", type="primary", use_container_width=True):
                results_log = []
                for i, contact in enumerate(targets):
                    progress_spot.progress((i + 1) / len(targets), text=f"Mailing {contact['name']}...")
                    try:
                        p_body = re.sub(r"\[Organization Name\]", contact.get('name', ''), st.session_state.letter_body, flags=re.IGNORECASE)
                        std_to = address_standard.StandardAddress.from_dict(contact)
                        std_from = address_standard.StandardAddress.from_dict(st.session_state.get("addr_from", {}))
                        pdf = letter_format.create_pdf(p_body, std_to, std_from, current_tier, st.session_state.get("signature_text"))
                        
                        success, resp = mailer.send_letter(pdf, std_to, std_from, current_tier)
                        if success:
                            st.session_state.campaign_metrics["sent"] += 1
                            results_log.append({"Name": contact['name'], "Status": "Success", "ID": resp})
                        else:
                            st.session_state.campaign_metrics["failed"] += 1
                            results_log.append({"Name": contact['name'], "Status": "Failed", "Error": str(resp)})
                    except Exception as e:
                        st.session_state.campaign_metrics["failed"] += 1
                        results_log.append({"Name": contact['name'], "Status": "Error", "Error": str(e)})

                    with metrics_spot.container():
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Target", len(targets))
                        c2.metric("Success ✅", st.session_state.campaign_metrics["sent"])
                        c3.metric("Failed ❌", st.session_state.campaign_metrics["failed"])

                progress_spot.empty(); st.balloons()
                st.download_button("📥 Result CSV", pd.DataFrame(results_log).to_csv(index=False), "results.csv", "text/csv")
                if mailer: mailer.send_email_notification(st.session_state.user_email, "Campaign Results", f"Success: {st.session_state.campaign_metrics['sent']}")
    else:
        # Standard Letter Logic
        if st.button("📄 Proof"):
            try:
                std_to = address_standard.StandardAddress.from_dict(st.session_state.get("addr_to", {}))
                std_from = address_standard.StandardAddress.from_dict(st.session_state.get("addr_from", {}))
                pdf = letter_format.create_pdf(st.session_state.letter_body, std_to, std_from, current_tier, st.session_state.get("signature_text"))
                st.markdown(f'<embed src="data:application/pdf;base64,{base64.b64encode(pdf).decode()}" width="100%" height="500" type="application/pdf">', unsafe_allow_html=True)
            except: st.error("Proof failed.")
        
        raw_total = pricing_engine.calculate_total(current_tier)
        final_total = max(0.0, raw_total - discount)
        st.markdown(f"### Total: ${final_total:.2f}")
        
        # --- FIXED PAYMENT BUTTON (FIXED: Missing line_items error) ---
        if st.button("💳 Pay", type="primary"):
            line_items = [{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": f"VerbaPost - {current_tier}"},
                    "unit_amount": int(final_total * 100)
                },
                "quantity": 1
            }]
            
            url = payment_engine.create_checkout_session(
                line_items=line_items, 
                user_email=st.session_state.get("user_email")
            )
            if url: st.link_button("👉 Click to Pay", url)

def render_application():
    if "app_mode" not in st.session_state: st.session_state.app_mode = "splash"
    mode = st.session_state.app_mode
    if mode == "splash": ui_splash.render_splash_page()
    elif mode == "login": ui_login.render_login_page()
    elif mode == "store": render_store_page()
    elif mode == "workspace": render_workspace_page()
    elif mode == "review": render_review_page()
    elif mode == "legal": ui_legal.render_legal_page()
    elif mode == "legacy": ui_legacy.render_legacy_page()
    else: st.session_state.app_mode = "splash"; st.rerun()

def render_main(): render_application()
if __name__ == "__main__": render_main()