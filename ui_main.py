import streamlit as st
from streamlit_drawable_canvas import st_canvas
import os
import tempfile
import json
import base64
import numpy as np
from PIL import Image
import io

# --- IMPORTS ---
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
from address_standard import StandardAddress

DEFAULT_URL = "https://verbapost.streamlit.app/"
YOUR_APP_URL = DEFAULT_URL
try:
    if secrets_manager:
        found_url = secrets_manager.get_secret("BASE_URL")
        if found_url: YOUR_APP_URL = found_url
except: pass
YOUR_APP_URL = YOUR_APP_URL.rstrip("/")

COUNTRIES = {
    "US": "United States", "CA": "Canada", "GB": "United Kingdom", "FR": "France",
    "DE": "Germany", "IT": "Italy", "ES": "Spain", "AU": "Australia", "MX": "Mexico",
    "JP": "Japan", "BR": "Brazil", "IN": "India"
}

def reset_app():
    recovered_draft = st.query_params.get("draft_id")
    keys = ["audio_path", "transcribed_text", "payment_complete", "sig_data", "to_addr", "civic_targets", "bulk_targets", "bulk_paid_qty", "is_intl", "is_certified", "letter_sent_success", "locked_tier", "w_to_name", "w_to_street", "w_to_street2", "w_to_city", "w_to_state", "w_to_zip", "w_to_country", "addr_book_idx", "last_tracking_num", "campaign_errors", "current_stripe_id", "current_draft_id"]
    for k in keys:
        if k in st.session_state: del st.session_state[k]
    st.session_state.to_addr = {}
    
    if recovered_draft:
        st.session_state.current_draft_id = recovered_draft
        st.session_state.app_mode = "workspace" 
        st.success("🔄 Session Restored!")
    elif st.session_state.get("user_email"): st.session_state.app_mode = "store"
    else: st.session_state.app_mode = "splash"

def render_hero(title, subtitle):
    # --- FIX 1: FORCE WHITE TEXT ON BLUE BACKGROUND ---
    # This explicit style overrides any global config settings
    st.markdown(f"""
    <div class="custom-hero" style="
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 40px;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 30px;
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);">
        <h1 style="margin: 0; font-size: 3rem; font-weight: 700; color: #ffffff !important; text-shadow: 0px 1px 2px rgba(0,0,0,0.2);">{title}</h1>
        <div style="font-size: 1.2rem; opacity: 0.95; margin-top: 10px; color: #ffffff !important;">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)

def render_legal_page(): import ui_legal; ui_legal.show_legal()

def render_store_page():
    u_email = st.session_state.get("user_email", "")
    if not u_email:
        st.warning("⚠️ Session Expired. Please log in to continue.")
        if st.button("Go to Login"): st.session_state.app_mode = "login"; st.rerun()
        return

    render_hero("Select Service", "Choose your letter type")
    is_admin = False
    try:
        if secrets_manager:
            admin_target = secrets_manager.get_secret("admin.email")
            if admin_target and str(u_email).lower() == str(admin_target).lower(): is_admin = True
    except: pass
    if is_admin:
        if st.button("🔐 Open Admin Console", type="secondary"): st.session_state.app_mode = "admin"; st.rerun()

    c1, c2 = st.columns([2, 1])
    with c1:
        with st.container(border=True):
            st.subheader("Available Packages")
            tier_options_list = ["Standard", "Heirloom", "Civic", "Santa", "Campaign"]
            tier_labels = {"Standard": "⚡ Standard ($2.99)", "Heirloom": "🏺 Heirloom ($5.99)", "Civic": "🏛️ Civic ($6.99)", "Santa": "🎅 Santa ($9.99)", "Campaign": "📢 Campaign (Bulk)"}
            tier_descriptions = {
                "Standard": "Your words professionally printed on standard paper and mailed via USPS First Class.",
                "Heirloom": "Printed on heavyweight archival stock with a wet-ink style font for a timeless look.",
                "Civic": "We automatically identify your local representatives and mail physical letters to them.",
                "Santa": "A magical letter from the North Pole on festive paper, signed by Santa Claus himself.",
                "Campaign": "Upload a CSV. We mail everyone at once."
            }
            pre_selected_index = 0
            if "target_marketing_tier" in st.session_state:
                target = st.session_state.target_marketing_tier
                if target in tier_options_list: pre_selected_index = tier_options_list.index(target)
            
            sel = st.radio("Select Tier", tier_options_list, format_func=lambda x: tier_labels[x], index=pre_selected_index, key="tier_selection_radio")
            tier_code = sel
            st.info(tier_descriptions[tier_code])
            
            qty = 1
            if tier_code == "Campaign":
                unit_price = 1.99
                qty = st.number_input("Number of Recipients", min_value=10, max_value=5000, value=50, step=10)
                price = 2.99 + ((qty - 1) * 1.99)
                st.caption(f"Pricing: First letter $2.99, then $1.99/ea")
            else:
                prices = {"Standard": 2.99, "Heirloom": 5.99, "Civic": 6.99, "Santa": 9.99}
                price = prices[tier_code]

            is_intl = False; is_certified = False
            if tier_code in ["Standard", "Heirloom"]:
                c_opt1, c_opt2 = st.columns(2)
                if c_opt1.checkbox("Send Internationally? (+$2.00)", key="intl_toggle_check"):
                    price += 2.00; is_intl = True
                if c_opt2.checkbox("📜 Certified Mail (+$12.00)"):
                    price += 12.00; is_certified = True; st.caption("Includes tracking & electronic proof.")

            st.session_state.is_intl = is_intl
            st.session_state.is_certified = is_certified

    with c2:
        with st.container(border=True):
            st.subheader("Checkout")
            discounted = False
            code_input = ""
            if promo_engine:
                code_input = st.text_input("Promo Code", key="promo_box")
                if code_input and promo_engine.validate_code(code_input): discounted = True; st.success("✅ Code Applied!")
            
            if discounted:
                st.metric("Total", "$0.00", delta=f"-${price:.2f} off")
                if st.button("🚀 Start (Free)", type="primary", use_container_width=True):
                    if promo_engine: promo_engine.log_usage(code_input, u_email)
                    if st.session_state.get("current_draft_id"):
                        d_id = st.session_state.current_draft_id
                        if database: database.update_draft_data(d_id, status="Draft", content="", tier=tier_code, price="0.00")
                    else:
                        if database: 
                            d_id = database.save_draft(u_email, "", tier_code, "0.00")
                            st.session_state.current_draft_id = d_id
                            st.query_params["draft_id"] = str(d_id)
                        
                    if audit_engine: audit_engine.log_event(u_email, "FREE_TIER_STARTED", None, {"code": code_input})
                    st.session_state.payment_complete = True; st.session_state.locked_tier = tier_code; st.session_state.bulk_paid_qty = qty if tier_code == "Campaign" else 1
                    st.session_state.app_mode = "workspace"; st.rerun()
            else:
                st.metric("Total", f"${price:.2f}")
                if st.button(f"Pay ${price:.2f} & Start", type="primary", use_container_width=True):
                    d_id = None
                    if st.session_state.get("current_draft_id"):
                        d_id = st.session_state.current_draft_id
                        if database: database.update_draft_data(d_id, status="Draft", tier=tier_code, price=price)
                    else:
                        if database: 
                            d_id = database.save_draft(u_email, "", tier_code, price)
                            st.session_state.current_draft_id = d_id
                            st.query_params["draft_id"] = str(d_id)
                    
                    link = f"{YOUR_APP_URL}?tier={tier_code}&session_id={{CHECKOUT_SESSION_ID}}"
                    if d_id: link += f"&draft_id={d_id}" 
                    if is_intl: link += "&intl=1"
                    if is_certified: link += "&certified=1"
                    if tier_code == "Campaign": link += f"&qty={qty}"

                    if payment_engine:
                        final_cents = int(price * 100)
                        url, sess_id = payment_engine.create_checkout_session(f"VerbaPost {tier_code}", final_cents, link, YOUR_APP_URL)
                        if url: st.markdown(f"""<a href="{url}" target="_blank" style="text-decoration:none;"><div style="background-color:#6772e5; color:white; padding:12px; border-radius:4px; text-align:center; font-weight:bold;">👉 Pay Now via Stripe</div></a>""", unsafe_allow_html=True)

def render_workspace_page():
    tier = st.session_state.get("locked_tier", "Standard")
    is_intl = st.session_state.get("is_intl", False)
    render_hero("Compose Letter", f"{tier} Edition")
    
    u_email = st.session_state.get("user_email")
    user_addr = {}
    if database and u_email:
        p = database.get_user_profile(u_email)
        if p: 
            user_addr = {
                "name": p.full_name, 
                "street": p.address_line1, 
                "address_line2": getattr(p, "address_line2", ""), 
                "city": p.address_city, 
                "state": p.address_state, 
                "zip": p.address_zip, 
                "country": getattr(p, "country", "US")
            }

    with st.container(border=True):
        if tier == "Campaign":
            st.subheader("📂 Upload Mailing List")
            if not bulk_engine: st.error("Bulk Engine Missing")
            st.info("""**CSV Format:** Name, Street, City, State, Zip""")
            uploaded_file = st.file_uploader("Upload CSV", type=['csv'])
            if uploaded_file:
                contacts, error = bulk_engine.parse_csv(uploaded_file)
                if error: st.error(error)
                else:
                    paid_qty = st.session_state.get("bulk_paid_qty", 1000)
                    if len(contacts) > paid_qty:
                        st.warning(f"⚠️ Limit Exceeded: You paid for {paid_qty} recipients but uploaded {len(contacts)}. The list has been truncated.")
                        contacts = contacts[:paid_qty] 
                    else:
                        st.success(f"✅ Loaded {len(contacts)} recipients.")
                    st.dataframe(contacts[:5])
                    if st.button("Confirm List"): st.session_state.bulk_targets = contacts; st.toast("List Saved!")
        
        else:
            # Prepare Defaults
            def_n=user_addr.get("name",""); def_s=user_addr.get("street","")
            def_s2=user_addr.get("address_line2",""); def_c=user_addr.get("city","")
            def_st=user_addr.get("state",""); def_z=user_addr.get("zip",""); def_cntry=user_addr.get("country","US")
            
            if tier == "Santa":
                st.info("🎅 **From:** Santa Claus, North Pole (Locked)")
                st.subheader("📍 Addressing")
                st.markdown("**📮 To (Recipient)**")
                st.text_input("Recipient Name", key="w_to_name")
                st.text_input("Recipient Street", key="w_to_street")
                st.text_input("Recipient Apt/Suite (Optional)", key="w_to_street2")
                c_city, c_state, c_zip = st.columns([2, 1, 1])
                c_city.text_input("City", key="w_to_city")
                c_state.text_input("State", key="w_to_state")
                c_zip.text_input("Zip", key="w_to_zip")
                st.session_state.w_to_country = "US"
                
                if st.button("Save Address", type="primary"):
                    _save_addresses_from_widgets(tier, False)
                    st.toast("Address Saved!")

            elif tier == "Civic":
                 st.subheader("🏛️ Your Representatives")
                 
                 # --- FIX 2: AUTOMATIC CIVIC LOOKUP ---
                 with st.expander("📍 Using your voting address (Click to Edit)", expanded=False):
                     c_f1, c_f2 = st.columns([1, 1])
                     with c_f1:
                         f_name = st.text_input("Your Name", value=def_n, key="w_from_name")
                         f_street = st.text_input("Street Address", value=def_s, key="w_from_street")
                         f_street2 = st.text_input("Apt/Suite", value=def_s2, key="w_from_street2")
                     with c_f2:
                         f_city = st.text_input("City", value=def_c, key="w_from_city")
                         f_state = st.text_input("State", value=def_st, key="w_from_state")
                         f_zip = st.text_input("Zip", value=def_z, key="w_from_zip")
                     st.session_state.w_from_country = "US"
                     
                     if st.button("🔄 Update Address & Search Again"):
                         if "civic_targets" in st.session_state: del st.session_state.civic_targets
                         st.rerun()

                 if "civic_targets" not in st.session_state:
                     full_addr = f"{f_street}, {f_city}, {f_state} {f_zip}"
                     if f_street and len(f_street) > 5 and civic_engine:
                         with st.spinner(f"🔍 Finding representatives for {f_street}..."):
                             reps = civic_engine.get_reps(full_addr)
                             if reps:
                                 st.session_state.civic_targets = reps
                                 st.rerun() 
                             else:
                                 st.error("Could not find representatives. Please check the address above.")
                     elif not f_street:
                         st.info("⚠️ Please ensure your address is set in your profile or enter it above.")

                 if "civic_targets" in st.session_state:
                     st.success(f"✅ Targets Identified: {len(st.session_state.civic_targets)} Elected Officials")
                     for r in st.session_state.civic_targets:
                         st.info(f"🏛️ **{r['title']} {r['name']}**")
                     st.caption("We will mail a physical letter to each of these officials.")

            else:
                st.subheader("📍 Addressing")
                with st.expander(f"✉️ From: {def_n} (Click to Edit)", expanded=False):
                    st.text_input("Sender Name", value=def_n, key="w_from_name")
                    st.text_input("Sender Street", value=def_s, key="w_from_street")
                    st.text_input("Sender Apt/Suite", value=def_s2, key="w_from_street2")
                    try: c_idx = list(COUNTRIES.keys()).index(def_cntry)
                    except: c_idx = 0
                    c_scntry, c_scity = st.columns([1, 2])
                    c_scntry.selectbox("From Country", list(COUNTRIES.keys()), format_func=lambda x: COUNTRIES[x], index=c_idx, key="w_from_country")
                    c_scity.text_input("Sender City", value=def_c, key="w_from_city")
                    c_sstate, c_szip = st.columns([1, 1])
                    c_sstate.text_input("State/Prov", value=def_st, key="w_from_state")
                    c_szip.text_input("Zip/Postal", value=def_z, key="w_from_zip")

                st.markdown("---")
                st.markdown("**📮 To (Recipient)**")
                
                if database:
                    contacts = database.get_contacts(u_email)
                    if contacts:
                        def _autofill_contact():
                            sel_idx = st.session_state.addr_book_idx
                            if sel_idx > 0:
                                c = contacts[sel_idx - 1]
                                st.session_state.w_to_name = c.name
                                st.session_state.w_to_street = c.street
                                st.session_state.w_to_street2 = getattr(c, 'street2', '') or getattr(c, 'address_line2', '')
                                st.session_state.w_to_city = c.city
                                st.session_state.w_to_state = c.state
                                st.session_state.w_to_zip = c.zip_code
                                st.session_state.w_to_country = c.country
                        contact_opts = ["-- Select from Address Book --"] + [c.name for c in contacts]
                        st.selectbox("📖 Address Book", range(len(contact_opts)), format_func=lambda x: contact_opts[x], key="addr_book_idx", on_change=_autofill_contact)

                st.text_input("Recipient Name", key="w_to_name")
                st.text_input("Recipient Street", key="w_to_street")
                st.text_input("Recipient Apt/Suite (Optional)", key="w_to_street2")
                
                if is_intl:
                    c_cntry, c_city = st.columns([1, 2])
                    c_cntry.selectbox("Recipient Country", list(COUNTRIES.keys()), format_func=lambda x: COUNTRIES[x], index=0, key="w_to_country")
                    c_city.text_input("Recipient City", key="w_to_city")
                    c_state, c_zip = st.columns([1, 1])
                    c_state.text_input("State/Province", key="w_to_state")
                    c_zip.text_input("Postal Code", key="w_to_zip")
                else:
                    c_city, c_state, c_zip = st.columns([2, 1, 1])
                    c_city.text_input("City", key="w_to_city")
                    c_state.text_input("State", key="w_to_state")
                    c_zip.text_input("Zip", key="w_to_zip")
                    st.session_state.w_to_country = "US"

                st.markdown("<br>", unsafe_allow_html=True)
                c_save1, c_save2 = st.columns([1, 2])
                
                if c_save1.button("Save Addresses", type="primary"):
                     check_name = st.session_state.get("w_to_name", "")
                     check_street = st.session_state.get("w_to_street", "")
                     if not check_name or not check_street:
                         st.error("⚠️ **Autofill Detected but not Saved:** Please click inside the Name and Street boxes to ensure the browser saves them.")
                     else:
                         _save_addresses_from_widgets(tier, is_intl)
                         d_id = st.session_state.get("current_draft_id")
                         if d_id and database:
                             database.update_draft_data(d_id, st.session_state.get("to_addr"), st.session_state.get("from_addr"))
                         st.toast("Addresses Saved to Database!")

                if c_save2.button("💾 Save to Address Book"):
                    name = st.session_state.get("w_to_name")
                    street = st.session_state.get("w_to_street")
                    if name and street:
                        database.add_contact(
                            u_email, name, street, 
                            st.session_state.get("w_to_street2", ""),
                            st.session_state.get("w_to_city"),
                            st.session_state.get("w_to_state"),
                            st.session_state.get("w_to_zip"),
                            st.session_state.get("w_to_country", "US")
                        )
                        st.success(f"Saved {name}!")
                        st.rerun()
                    else: st.error("Enter Name & Street first.")

    st.write("---")
    c_sig, c_mic = st.columns(2)
    with c_sig:
        st.write("✍️ **Signature**")
        if tier == "Santa": st.info("Signed by Santa"); st.session_state.sig_data = None
        else:
             canvas = st_canvas(stroke_width=2, stroke_color="#000", background_color="#fff", height=150, width=400, key="canvas")
             if canvas.image_data is not None: st.session_state.sig_data = canvas.image_data
    
    with c_mic:
        st.write("🎤 **Input Source**")
        t_rec, t_up = st.tabs(["🔴 Record", "📂 Upload File"])
        
        with t_rec:
            audio = st.audio_input("Record Voice Note")
            if audio:
                if ai_engine:
                    with st.spinner("Transcribing..."):
                        text = ai_engine.transcribe_audio(audio)
                        st.session_state.transcribed_text = text
                        st.session_state.app_mode = "review"
                        st.rerun()

        with t_up:
            st.caption("Max 25MB. Supported: wav, mp3, m4a, mp4.")
            uploaded_file = st.file_uploader("Select Audio File", type=['wav', 'mp3', 'm4a', 'mp4', 'webm'])
            if uploaded_file is not None:
                if st.button("Transcribe File", type="primary"):
                    if ai_engine:
                        if uploaded_file.size > 25 * 1024 * 1024:
                            st.error("⚠️ File too large (>25MB). Please compress it.")
                        else:
                            with st.spinner("Uploading & Transcribing..."):
                                file_ext = uploaded_file.name.split('.')[-1]
                                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp:
                                    tmp.write(uploaded_file.getvalue())
                                    tmp_path = tmp.name
                                try:
                                    text = ai_engine.transcribe_audio(tmp_path)
                                    st.session_state.transcribed_text = text
                                    st.session_state.app_mode = "review"
                                    st.rerun()
                                except Exception as e: st.error(f"Transcription Failed: {e}")
                                finally:
                                    if os.path.exists(tmp_path): os.remove(tmp_path)

def _save_addresses_from_widgets(tier, is_intl):
    if tier == "Santa":
        st.session_state.from_addr = {
            "name": "Santa Claus", "street": "123 Elf Road", "city": "North Pole", "state": "NP", "zip": "88888", "country": "NP"
        }
    else:
        st.session_state.from_addr = {
            "name": st.session_state.get("w_from_name"),
            "street": st.session_state.get("w_from_street"),
            "address_line2": st.session_state.get("w_from_street2", ""),
            "city": st.session_state.get("w_from_city"),
            "state": st.session_state.get("w_from_state"),
            "zip": st.session_state.get("w_from_zip"),
            "country": st.session_state.get("w_from_country", "US"),
            "email": st.session_state.get("user_email")
        }
    
    if tier == "Civic":
        st.session_state.to_addr = {
            "name": "Civic Action", "street": "Capitol", "city": "DC", "state": "DC", "zip": "20000", "country": "US"
        }
    else:
        st.session_state.to_addr = {
            "name": st.session_state.get("w_to_name"),
            "street": st.session_state.get("w_to_street"),
            "address_line2": st.session_state.get("w_to_street2", ""),
            "city": st.session_state.get("w_to_city"),
            "state": st.session_state.get("w_to_state"),
            "zip": st.session_state.get("w_to_zip"),
            "country": st.session_state.get("w_to_country", "US")
        }

def render_review_page():
    render_hero("Review Letter", "Finalize and Send")
    if "letter_sent_success" not in st.session_state: st.session_state.letter_sent_success = False
    
    if st.button("⬅️ Edit Text or Addresses", type="secondary"):
        st.session_state.app_mode = "workspace"; st.rerun()
    
    tier = st.session_state.get("locked_tier", "Standard")
    is_intl = st.session_state.get("is_intl", False)
    is_certified = st.session_state.get("is_certified", False)

    if tier != "Campaign" and (not st.session_state.get("to_addr") or not st.session_state.get("from_addr")):
        _save_addresses_from_widgets(tier, is_intl)

    if tier == "Civic" and "civic_targets" in st.session_state:
        st.info(f"🏛️ **Mailing to {len(st.session_state.civic_targets)} representatives**")
    if tier == "Campaign" and "bulk_targets" in st.session_state:
        st.info(f"📢 **Campaign Mode:** Mailing to {len(st.session_state.bulk_targets)} recipients.")

    st.write("✨ **AI Magic Editor**")
    c_edit1, c_edit2, c_edit3, c_edit4 = st.columns(4)
    def run_edit(style):
        curr_text = st.session_state.get("transcribed_text", "")
        if not curr_text: st.error("⚠️ No text to edit!"); return
        if ai_engine:
            with st.spinner(f"✨ Rewriting..."):
                new_text = ai_engine.refine_text(curr_text, style)
                if new_text and len(new_text.strip()) > 5:
                    st.session_state.transcribed_text = new_text; st.rerun()
                else: st.error("⚠️ AI Error: Returned empty text. Original text preserved.")

    if c_edit1.button("✅ Fix Grammar", use_container_width=True): run_edit("Grammar")
    if c_edit2.button("👔 Professional", use_container_width=True): run_edit("Professional")
    if c_edit3.button("🤗 Friendly", use_container_width=True): run_edit("Friendly")
    if c_edit4.button("✂️ Concise", use_container_width=True): run_edit("Concise")

    st.info("📝 **Note:** You can edit the text below directly. The AI buttons above are optional.")
    txt = st.text_area("Body Content", key="transcribed_text", height=300, disabled=st.session_state.letter_sent_success)
    
    if st.button("👁️ Preview PDF Proof", type="secondary", use_container_width=True):
        if not txt or len(txt.strip()) < 5:
            st.error("⚠️ Cannot preview empty letter.")
        else:
            to_p = st.session_state.get("to_addr") or {"name": "Preview", "street": "123 St", "city": "City", "state": "ST", "zip": "12345", "country": "US"}
            from_p = st.session_state.get("from_addr") or {"name": "Sender", "street": "123 St", "city": "City", "state": "ST", "zip": "12345", "country": "US"}
            
            with st.spinner("Generating Proof..."):
                to_std = StandardAddress.from_dict(to_p)
                to_str = to_std.to_pdf_string()
                from_std = StandardAddress.from_dict(from_p)
                from_str = from_std.to_pdf_string()
                
                sig_path = None
                if st.session_state.get("sig_data") is not None:
                     try:
                        img = Image.fromarray(st.session_state.sig_data.astype('uint8'), 'RGBA')
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                            img.save(tmp.name); sig_path = tmp.name
                     except: pass

                if letter_format:
                    pdf_bytes = letter_format.create_pdf(txt, to_str, from_str, is_heirloom=("Heirloom" in tier), is_santa=("Santa" in tier), signature_path=sig_path)
                    if pdf_bytes:
                        b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
                        st.markdown(f'<iframe src="data:application/pdf;base64,{b64_pdf}" width="100%" height="500"></iframe>', unsafe_allow_html=True)
                
                if sig_path:
                    try: os.remove(sig_path)
                    except: pass

    if not st.session_state.letter_sent_success:
        if st.button("🚀 Send Letter", type="primary"):
            if not txt or len(txt.strip()) < 10:
                st.error("⚠️ **Letter is too short or empty!** Please write more content."); return

            targets = []
            if tier == "Campaign": 
                targets = st.session_state.get("bulk_targets", [])
                if not targets: st.error("⚠️ No mailing list found. Please upload a CSV first."); st.stop()
            elif tier == "Civic" and "civic_targets" in st.session_state:
                for rep in st.session_state.civic_targets: 
                    t = rep.get('address_obj')
                    if t: t['country'] = 'US'; targets.append(t) 
            else:
                if not st.session_state.get("to_addr"): st.error("⚠️ Recipient Address missing."); return
                targets.append(st.session_state.to_addr)

            if tier != "Campaign":
                if not st.session_state.get("from_addr") and tier != "Santa":
                    st.error("⚠️ Sender Address missing."); return

            current_stripe_id = st.session_state.get("current_stripe_id")
            u_email = st.session_state.get("user_email")
            d_id = st.session_state.get("current_draft_id")

            try:
                with st.spinner("Processing & Mailing..."):
                    from_data = st.session_state.get("from_addr", {})
                    sig_path = None; sig_db_value = None
                    is_santa = (tier == "Santa")
                    if not is_santa and st.session_state.get("sig_data") is not None:
                        try:
                            img_data = st.session_state.sig_data
                            img = Image.fromarray(img_data.astype('uint8'), 'RGBA')
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_sig:
                                img.save(tmp_sig.name); sig_path = tmp_sig.name
                            buf = io.BytesIO(); img.save(buf, format="PNG"); sig_db_value = base64.b64encode(buf.getvalue()).decode("utf-8")
                        except: pass

                    prog_bar = st.progress(0); errors = []; successful_count = 0
                    
                    for i, to_data in enumerate(targets):
                        to_std = StandardAddress.from_dict(to_data)
                        to_str = to_std.to_pdf_string()
                        if tier == "Santa": from_str = "Santa Claus"
                        else:
                            from_std = StandardAddress.from_dict(from_data)
                            from_str = from_std.to_pdf_string()

                        if letter_format:
                            pdf_bytes = letter_format.create_pdf(txt, to_str, from_str, is_heirloom=("Heirloom" in tier), is_santa=is_santa, signature_path=sig_path)
                            
                            is_pg_ok = False
                            if (tier == "Standard" or tier == "Civic" or tier == "Campaign") and mailer:
                                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp: tmp.write(pdf_bytes); tmp_path = tmp.name
                                
                                success, resp = mailer.send_letter(tmp_path, to_data, from_data, certified=is_certified)
                                
                                try:
                                    if os.path.exists(tmp_path): os.remove(tmp_path)
                                except: pass
                                
                                if success:
                                    is_pg_ok = True; successful_count += 1
                                    if is_certified and resp.get('trackingNumber'): st.session_state.last_tracking_num = resp.get('trackingNumber')
                                    if audit_engine: audit_engine.log_event(u_email, "MAIL_SENT_SUCCESS", current_stripe_id, {"provider_id": resp.get('id')})
                                else:
                                    is_pg_ok = False; errors.append(f"{to_data.get('name')}: {resp}")
                                    if audit_engine: audit_engine.log_event(u_email, "MAIL_API_FAILURE", current_stripe_id, {"error": str(resp)})

                            if database:
                                final_status = "Pending Admin"
                                if tier in ["Standard", "Civic", "Campaign"]: final_status = "Completed" if is_pg_ok else "Failed/Retry"
                                
                                if d_id: database.update_draft_data(d_id, to_data, from_data, content=txt, status=final_status)
                                else: database.save_draft(u_email, txt, tier, "0.00", to_addr=to_data, from_addr=from_data, status=final_status, sig_data=sig_db_value)
                                
                                if (tier == "Santa" or tier == "Heirloom") and mailer: mailer.send_admin_alert(u_email, txt, tier)

                        prog_bar.progress((i + 1) / len(targets))

                    if sig_path:
                        try: os.remove(sig_path)
                        except: pass
                    
                    if errors: 
                        st.session_state.campaign_errors = errors
                        if tier == "Campaign": st.warning(f"Sent: {successful_count} | Failed: {len(errors)}")
                    
                    if tier != "Campaign":
                        if errors: st.error("❌ Delivery Failed. See details below."); return
                        else: st.session_state.letter_sent_success = True; st.rerun()
                    else: st.session_state.letter_sent_success = True; st.rerun()

            except Exception as e:
                st.error(f"Critical Error: {e}")
                if audit_engine: audit_engine.log_event(u_email, "APP_CRASH_DURING_SEND", current_stripe_id, {"trace": str(e)})

    else:
        if st.session_state.get("campaign_errors"):
            st.error(f"⚠️ {len(st.session_state.campaign_errors)} failed.")
            with st.expander("View Errors"):
                for e in st.session_state.campaign_errors: st.write(e)
            del st.session_state.campaign_errors
        else: st.success("✅ Letters Queued for Delivery!")
            
        if st.session_state.get("last_tracking_num"):
            st.info(f"📜 **Certified Mail Tracking:** {st.session_state.last_tracking_num}")
            st.caption("You will also receive this via email.")
        
        if st.button("🏁 Success! Send Another Letter", type="primary", use_container_width=True):
            reset_app()
            st.rerun()