import streamlit as st
import pandas as pd
import io
import time
import base64
import logging
import json
import os
from datetime import datetime

# --- ENGINES & UTILS ---
# Importing all original backend engines to maintain full functionality
import database
import ai_engine
import letter_format
import mailer
import payment_engine
import audit_engine
import bulk_engine
from address_standard import StandardAddress

logger = logging.getLogger(__name__)

# --- STYLES & UI HELPERS (ORIGINAL VERBOSE CSS) ---
def inject_custom_css():
    """Applies the professional/minimalist design language as defined in the original splash release."""
    st.markdown("""
        <style>
        .main { background-color: #fcfcfc; }
        .stButton>button { border-radius: 4px; font-weight: 500; height: 3rem; border: 1px solid #ddd; }
        .stButton>button:hover { border-color: #d93025; color: #d93025; }
        .stTabs [data-baseweb="tab-list"] { gap: 8px; }
        .stTabs [data-baseweb="tab"] {
            background-color: #f8f9fa;
            border-radius: 4px 4px 0 0;
            padding: 10px 20px;
            font-weight: 600;
        }
        .stTabs [aria-selected="true"] { 
            background-color: #fff !important; 
            border-bottom: 3px solid #d93025 !important; 
            color: #d93025 !important;
        }
        .tier-card {
            border: 1px solid #eaeaea;
            border-radius: 8px;
            padding: 24px;
            background: white;
            transition: all 0.3s ease;
            text-align: center;
        }
        .tier-card:hover { 
            transform: translateY(-5px); 
            border-color: #d93025; 
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        }
        .section-header {
            font-family: 'Merriweather', serif;
            font-size: 1.5rem;
            color: #111;
            margin-bottom: 1rem;
            border-left: 4px solid #d93025;
            padding-left: 10px;
        }
        </style>
    """, unsafe_allow_html=True)

def render_hero(title, subtitle):
    """Standardized hero header for all app views to maintain design consistency."""
    st.markdown(f"""
        <div style="text-align: center; padding: 2.5rem 0; border-bottom: 1px solid #eee; margin-bottom: 2.5rem;">
            <h1 style="font-family: 'Merriweather', serif; font-size: 3.2rem; margin-bottom: 0.5rem; color: #111;">{title}</h1>
            <p style="color: #d93025; font-weight: 700; text-transform: uppercase; letter-spacing: 2.5px; font-size: 0.9rem;">{subtitle}</p>
        </div>
    """, unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
def init_state():
    """Initializes all required session variables to prevent KeyErrors during navigation."""
    if "step" not in st.session_state: st.session_state.step = 1
    if "tier" not in st.session_state: st.session_state.tier = "Standard"
    if "letter_content" not in st.session_state: st.session_state.letter_content = ""
    if "addr_from" not in st.session_state: st.session_state.addr_from = {}
    if "addr_to" not in st.session_state: st.session_state.addr_to = {}
    if "pdf_ready" not in st.session_state: st.session_state.pdf_ready = False
    if "user_email" not in st.session_state: st.session_state.user_email = "guest"
    if "user_id" not in st.session_state: st.session_state.user_id = None
    if "promo_code" not in st.session_state: st.session_state.promo_code = ""
    if "discount" not in st.session_state: st.session_state.discount = 0.0
    if "found_reps" not in st.session_state: st.session_state.found_reps = []
    if "campaign_results" not in st.session_state: st.session_state.campaign_results = None
    if "show_preview" not in st.session_state: st.session_state.show_preview = False

def reset_app():
    """Full application reset logic to return to clean state."""
    st.session_state.step = 1
    st.session_state.letter_content = ""
    st.session_state.addr_to = {}
    st.session_state.pdf_ready = False
    st.session_state.found_reps = []
    st.session_state.discount = 0.0
    st.session_state.promo_code = ""
    st.rerun()

# --- STEP 1: THE STORE (MAINTAINING ALL ORIGINAL UI BLOCKS) ---
def render_store():
    render_hero("The VerbaPost Store", "SELECT YOUR MAILING EXPERIENCE")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="tier-card">', unsafe_allow_html=True)
        st.markdown("### ✉️ Standard")
        st.write("First class mail on archival bond paper. Clean, professional, and reliable.")
        st.markdown("<h2 style='color: #d93025;'>$2.99</h2>", unsafe_allow_html=True)
        if st.button("Select Standard", use_container_width=True, key="btn_std_original"):
            st.session_state.tier = "Standard"
            st.session_state.step = 2
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="tier-card">', unsafe_allow_html=True)
        st.markdown("### 🏛️ Civic")
        st.write("Write to your Senators or Reps. We find their official addresses for you.")
        st.markdown("<h2 style='color: #d93025;'>$6.99</h2>", unsafe_allow_html=True)
        if st.button("Select Civic", use_container_width=True, key="btn_civ_original"):
            st.session_state.tier = "Civic"
            st.session_state.step = 2
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="tier-card">', unsafe_allow_html=True)
        st.markdown("### 🎨 Heirloom")
        st.write("Preserve stories with custom handwriting fonts and premium textured parchment.")
        st.markdown("<h2 style='color: #d93025;'>$9.99</h2>", unsafe_allow_html=True)
        if st.button("Select Heirloom", use_container_width=True, key="btn_hrl_original"):
            st.session_state.tier = "Heirloom"
            st.session_state.step = 2
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    with st.container(border=True):
        col_bulk_text, col_bulk_btn = st.columns([2, 1])
        with col_bulk_text:
            st.markdown("### 📬 Bulk Campaigns")
            st.write("Perfect for senior volunteer groups and community organizations. Upload your mailing list and we'll handle the rest.")
        with col_bulk_btn:
            st.write("") # Padding
            if st.button("Open Campaign Manager", type="primary", use_container_width=True, key="btn_bulk_original"):
                st.session_state.tier = "Campaign"
                st.session_state.step = 2
                st.rerun()

# --- STEP 2: THE WORKSPACE ---

def render_addressing_section():
    """Comprehensive addressing logic including the original Address Book selection code."""
    st.markdown('<div class="section-header">1. Addressing</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    
    with c1:
        st.write("**Sender Information (Return Address)**")
        f_name = st.text_input("Full Name", value=st.session_state.addr_from.get('name',''), key="f_n_orig")
        f_street = st.text_input("Street Address", value=st.session_state.addr_from.get('street',''), key="f_s_orig")
        f_c = st.columns([2, 1, 1])
        f_city = f_c[0].text_input("City", value=st.session_state.addr_from.get('city',''), key="f_c_orig")
        f_state = f_c[1].text_input("State", value=st.session_state.addr_from.get('state',''), key="f_st_orig")
        f_zip = f_c[2].text_input("Zip", value=st.session_state.addr_from.get('zip',''), key="f_z_orig")
        st.session_state.addr_from = {"name": f_name, "street": f_street, "city": f_city, "state": f_state, "zip": f_zip}

    with c2:
        if st.session_state.tier == "Campaign":
            st.info("💡 Recipients are managed via the Campaign CSV uploader below.")
        else:
            st.write("**Recipient Information**")
            # ORIGINAL ADDRESS BOOK SELECTOR
            contacts = database.get_contacts(st.session_state.user_email)
            if contacts:
                c_names = ["-- Choose from Address Book --"] + [c['name'] for c in contacts]
                sel = st.selectbox("Saved Contacts", c_names, key="addr_book_orig")
                if sel != "-- Choose from Address Book --":
                    match = next(c for c in contacts if c['name'] == sel)
                    st.session_state.addr_to = match

            t_name = st.text_input("Recipient Name", value=st.session_state.addr_to.get('name',''), key="t_n_orig")
            t_street = st.text_input("Street Address", value=st.session_state.addr_to.get('street',''), key="t_s_orig")
            t_c = st.columns([2, 1, 1])
            t_city = t_c[0].text_input("City", value=st.session_state.addr_to.get('city',''), key="t_c_orig")
            t_state = t_c[1].text_input("State", value=st.session_state.addr_to.get('state',''), key="t_st_orig")
            t_zip = t_c[2].text_input("Zip", value=st.session_state.addr_to.get('zip',''), key="t_z_orig")
            st.session_state.addr_to = {"name": t_name, "street": t_street, "city": t_city, "state": t_state, "zip": t_zip}

def render_composition_section():
    """Original composition logic with Whisper audio and GPT refinement buttons."""
    st.markdown('<div class="section-header">2. Composition</div>', unsafe_allow_html=True)
    
    # ORIGINAL AUDIO WIDGET
    audio_data = st.audio_input("Dictate your letter directly")
    if audio_data:
        with st.spinner("VerbaPost AI is transcribing your voice..."):
            transcript = ai_engine.transcribe_audio(audio_data)
            st.session_state.letter_content = transcript

    st.session_state.letter_content = st.text_area(
        "Write or edit your content here:", 
        value=st.session_state.letter_content, 
        height=380,
        placeholder="Type your message, or use the microphone to dictate..."
    )

    # ORIGINAL AI REFINEMENT ROW
    c_ref1, c_ref2, c_ref3 = st.columns(3)
    if c_ref1.button("✨ Professional Tone", use_container_width=True, key="ref_prof"):
        st.session_state.letter_content = ai_engine.refine_text(st.session_state.letter_content, "Professional")
        st.rerun()
    if c_ref2.button("🎈 Warm & Friendly", use_container_width=True, key="ref_warm"):
        st.session_state.letter_content = ai_engine.refine_text(st.session_state.letter_content, "Warm")
        st.rerun()
    if c_ref3.button("🧹 Clean Grammar", use_container_width=True, key="ref_gram"):
        st.session_state.letter_content = ai_engine.refine_text(st.session_state.letter_content, "Grammar")
        st.rerun()

def render_civic_feature():
    """Full Civic search integration from the original source."""
    st.markdown('<div class="section-header">🏛️ Advocacy Lookup</div>', unsafe_allow_html=True)
    st.write("We use Geocodio to find your federal and state representatives based on your return address.")
    
    if st.button("🔍 Find My Representatives", use_container_width=True, key="civic_search_btn"):
        from civic_engine import find_representatives
        with st.spinner("Connecting to Geocodio..."):
            reps = find_representatives(st.session_state.addr_from)
            if reps:
                st.session_state.found_reps = reps
                st.success(f"Success! We found {len(reps)} officials for your district.")
            else:
                st.error("Address lookup failed. Please check your 'From' address and try again.")

    if st.session_state.found_reps:
        for rep in st.session_state.found_reps:
            with st.container(border=True):
                col_r1, col_r2 = st.columns([4, 1])
                col_r1.markdown(f"**{rep['name']}** \n*{rep['office']}*")
                if col_r2.button("Choose", key=f"sel_r_{rep['name']}"):
                    st.session_state.addr_to = rep['address']
                    st.session_state.addr_to['name'] = rep['name']
                    st.toast(f"Recipient set to {rep['name']}!")
                    st.rerun()

# --- CAMPAIGN COMPONENT (NOW INTEGRATED WITH PROGRESS, PERSONALIZATION & EXPORT) ---
def render_campaign_manager():
    """Meticulously preserved Campaign UI with the requested Progress, Personalized Greeting, and Download features."""
    st.markdown('<div class="section-header">📬 Bulk Campaign Manager</div>', unsafe_allow_html=True)
    st.info("Upload your recipient list in CSV format (name, street, city, state, zip).")
    
    csv_file = st.file_uploader("Upload Mailing List", type="csv", key="bulk_upload_original")
    
    if csv_file:
        contacts = bulk_engine.parse_csv(csv_file)
        if not contacts:
            st.error("Error parsing file. Check headers: name, street, city, state, zip")
            return

        st.success(f"Validated {len(contacts)} recipients.")
        with st.expander("Review Recipient List (First 10)"):
            st.table(contacts[:10])

        if st.button("🚀 Execute Bulk Campaign", type="primary", use_container_width=True, key="bulk_run_btn"):
            if not st.session_state.letter_content:
                st.error("Workspace error: Letter body cannot be empty for a campaign.")
                return
            
            # RESULTS TRACKING
            results_log = []
            success_count = 0
            fail_count = 0
            
            # REAL-TIME PROGRESS BAR
            prog_bar = st.progress(0, text="Initializing mailing systems...")
            
            for i, contact in enumerate(contacts):
                # UPDATE PROGRESS
                progress = int(((i + 1) / len(contacts)) * 100)
                prog_bar.progress(progress, text=f"Dispatching to {contact['name']} ({i+1}/{len(contacts)})")
                
                try:
                    # DYNAMIC PERSONALIZATION: Populating the greeting line
                    personalized_body = st.session_state.letter_content.replace("[Organization Name]", contact['name'])
                    
                    # Generate unique PDF for this recipient
                    current_pdf = letter_format.generate_letter_pdf(
                        personalized_body,
                        st.session_state.addr_from,
                        contact,
                        st.session_state.tier
                    )
                    
                    # SEND VIA MAILER
                    addr_obj = StandardAddress.from_dict(contact)
                    success, response = mailer.send_letter(
                        current_pdf, 
                        addr_obj, 
                        st.session_state.addr_from, 
                        "Campaign"
                    )
                    
                    if success:
                        success_count += 1
                        results_log.append({"Name": contact['name'], "Status": "Success", "LetterID": response})
                        audit_engine.log_event(st.session_state.user_email, "LETTER_SENT", f"Bulk mail: {contact['name']}", {"id": response})
                    else:
                        fail_count += 1
                        results_log.append({"Name": contact['name'], "Status": "Failed", "Error": str(response)})
                except Exception as e:
                    fail_count += 1
                    results_log.append({"Name": contact['name'], "Status": "Crash", "Error": str(e)})

            # CLEANUP & BALLOONS
            prog_bar.empty()
            st.balloons()
            st.success(f"Execution Complete: {success_count} letters successfully dispatched. {fail_count} failed.")
            
            # EXPORT CSV BUTTON
            res_df = pd.DataFrame(results_log)
            csv_output = io.StringIO()
            res_df.to_csv(csv_output, index=False)
            
            st.download_button(
                label="📥 Download Campaign Delivery Results (CSV)",
                data=csv_output.getvalue(),
                file_name=f"verbapost_bulk_results_{int(time.time())}.csv",
                mime="text/csv",
                use_container_width=True,
                key="bulk_download_btn"
            )

def render_workspace():
    """Full-length Step 2 Controller as found in the original 574-line release."""
    render_hero("The Workspace", f"COMPOSING YOUR {st.session_state.tier.upper()} LETTER")
    
    # 1. ADDRESSING BLOCK
    render_addressing_section()
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 2. COMPOSITION BLOCK
    render_composition_section()
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 3. TIER-SPECIFIC FEATURES
    if st.session_state.tier == "Civic":
        render_civic_feature()
        st.markdown("<br>", unsafe_allow_html=True)
    
    if st.session_state.tier == "Campaign":
        render_campaign_manager()
        st.markdown("<br>", unsafe_allow_html=True)

    # 4. NAVIGATION BAR
    st.markdown("---")
    nav_c1, nav_c2 = st.columns(2)
    with nav_c1:
        if st.button("← Choose Different Tier", use_container_width=True, key="nav_back_store"):
            st.session_state.step = 1
            st.rerun()
    with nav_c2:
        if st.button("Review & Finalize →", type="primary", use_container_width=True, key="nav_to_review"):
            if not st.session_state.letter_content:
                st.warning("Please write your letter before proceeding.")
            else:
                st.session_state.step = 3
                st.rerun()

# --- STEP 3: REVIEW & PAYMENT (MAINTAINING ORIGINAL VERBOSE LOGIC) ---

def render_review():
    """Final typesetting, PDF preview, and Stripe checkout logic."""
    render_hero("Review & Send", "PHYSICAL MAIL IS PERMANENT")
    
    st.info("Please review the PDF below. This is exactly how your letter will appear when printed.")
    
    # 1. TYPESETTING & PREVIEW
    with st.spinner("Formatting your archival PDF..."):
        try:
            # ORIGINAL PDF GENERATION CALL
            pdf_bytes = letter_format.generate_letter_pdf(
                st.session_state.letter_content,
                st.session_state.addr_from,
                st.session_state.addr_to,
                st.session_state.tier
            )
            # EMBEDDING FOR BROWSER
            b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
            embed_code = f'<embed src="data:application/pdf;base64,{b64_pdf}" width="100%" height="750" type="application/pdf">'
            st.markdown(embed_code, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Typesetting Error: {e}. Please ensure your content is not too long.")

    st.markdown("<br>", unsafe_allow_html=True)
    
    # 2. PROMO & PAYMENT ROW
    col_rev_a, col_rev_b = st.columns([1.5, 1])
    
    with col_rev_a:
        st.markdown("#### Letter Specifications")
        st.write(f"**Mailing Tier:** {st.session_state.tier}")
        st.write(f"**From:** {st.session_state.addr_from.get('name')}")
        st.write(f"**To:** {st.session_state.addr_to.get('name', 'Multiple Recipients' if st.session_state.tier == 'Campaign' else 'N/A')}")
        
        # PROMO SECTION
        st.write("")
        with st.expander("🎟️ Apply Promo Code"):
            p_code_raw = st.text_input("Coupon", key="coupon_orig")
            if st.button("Apply", key="apply_promo_btn"):
                valid, discount_val = database.validate_promo(p_code_raw)
                if valid:
                    st.session_state.promo_code = p_code_raw
                    st.session_state.discount = discount_val
                    st.success(f"Success! Discount applied: -${discount_val}")
                else:
                    st.error("Promo code invalid or expired.")

    with col_rev_b:
        st.markdown("#### Secure Checkout")
        
        # ORIGINAL PRICE CALCULATION
        base_costs = {"Standard": 2.99, "Civic": 6.99, "Heirloom": 9.99, "Campaign": 0.0}
        tier_price = base_costs.get(st.session_state.tier, 2.99)
        checkout_total = max(0.0, tier_price - st.session_state.discount)
        
        st.markdown(f"### Total: ${checkout_total:.2f}")
        
        # STRIPE REDIRECT LOGIC
        if st.button("💳 Confirm and Pay", type="primary", use_container_width=True, key="pay_btn_orig"):
            stripe_url = payment_engine.create_checkout_session(
                user_email=st.session_state.user_email,
                tier=st.session_state.tier,
                price=checkout_total,
                metadata={
                    "content": st.session_state.letter_content,
                    "addr_from": json.dumps(st.session_state.addr_from),
                    "addr_to": json.dumps(st.session_state.addr_to)
                }
            )
            if stripe_url:
                # ORIGINAL REFRESH REDIRECT
                st.markdown(f'<meta http-equiv="refresh" content="0;url={stripe_url}">', unsafe_allow_html=True)
                st.info("Handing off to Stripe Secure Checkout...")
            else:
                st.error("Stripe gateway is currently unavailable. Please try again in 10 minutes.")

    # 3. FINAL NAV
    if st.button("← Edit Letter Content", use_container_width=True, key="back_to_work_rev"):
        st.session_state.step = 2
        st.rerun()

# --- ENTRY POINT & ROUTING (CRITICAL ENTRY FUNCTION) ---

def render_main():
    """Original top-level router for the entire VerbaPost UI."""
    inject_custom_css()
    init_state()
    
    # NAVIGATION BAR (IF LOGGED IN)
    if st.session_state.get("authenticated"):
        with st.sidebar:
            st.markdown("### VerbaPost Menu")
            if st.button("🏠 Store Home", use_container_width=True): reset_app()
            if st.button("📜 Letter History", use_container_width=True): st.session_state.app_mode = "history"; st.rerun()
            st.markdown("---")
            st.write(f"User: {st.session_state.user_email}")
            if st.button("🚪 Logout", use_container_width=True): 
                st.session_state.authenticated = False
                st.session_state.app_mode = "splash"
                st.rerun()

    # STEP ROUTING
    if st.session_state.step == 1:
        render_store()
    elif st.session_state.step == 2:
        render_workspace()
    elif st.session_state.step == 3:
        render_review()

if __name__ == "__main__":
    render_main()