import streamlit as st
from streamlit_drawable_canvas import st_canvas

# --- IMPORTS ---
try: import database
except: database = None
try: import ai_engine
except: ai_engine = None
try: import letter_format
except: letter_format = None

# --- CONFIG ---
YOUR_APP_URL = "https://verbapost.streamlit.app/" 

def render_hero(title, subtitle):
    # FIXED: Added !important to force White text despite Global Light Mode
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); 
                padding: 40px; border-radius: 15px; text-align: center; 
                margin-bottom: 30px; box-shadow: 0 8px 16px rgba(0,0,0,0.1);">
        <h1 style="margin: 0; font-size: 3rem; font-weight: 700; color: white !important;">{title}</h1>
        <div style="font-size: 1.2rem; opacity: 0.9; margin-top: 10px; color: #e0e0e0 !important;">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)

def show_main_app():
    if "app_mode" not in st.session_state: st.session_state.app_mode = "store"
    if "session_id" in st.query_params:
        st.session_state.payment_complete = True
        st.session_state.app_mode = "workspace"
        st.query_params.clear()

    if st.session_state.get("payment_complete"): render_workspace_page()
    elif st.session_state.app_mode == "store": render_store_page()
    elif st.session_state.app_mode == "review": render_review_page()
    else: render_store_page()

def render_store_page():
    render_hero("Select Service", "Choose your letter type")
    c1, c2 = st.columns([2, 1])
    with c1:
        with st.container(border=True):
            st.subheader("Letter Options")
            tier = st.radio("Select Tier", ["⚡ Standard ($2.99)", "🏺 Heirloom ($5.99)", "🏛️ Civic ($6.99)"])
            lang = st.selectbox("Language", ["English", "Spanish", "French"])
    with c2:
        with st.container(border=True):
            st.subheader("Checkout")
            st.metric("Total", "$2.99")
            if st.button("Pay & Start", type="primary", use_container_width=True):
                st.session_state.payment_complete = True
                st.session_state.locked_tier = tier
                st.session_state.app_mode = "workspace"
                st.rerun()

def render_workspace_page():
    tier = st.session_state.get("locked_tier", "Standard")
    render_hero("Compose Letter", f"{tier} Edition")
    
    # --- AUTO-POPULATE LOGIC ---
    user_email = ""
    if st.session_state.get("user"):
        u = st.session_state.user
        if hasattr(u, "email"): user_email = u.email
        elif hasattr(u, "user"): user_email = u.user.email
        elif isinstance(u, dict): user_email = u.get("email", "")

    profile = {}
    if database and user_email:
        profile = database.get_user_profile(user_email)
    
    def_name = profile.get("full_name", "")
    def_street = profile.get("address_line1", "")
    def_city = profile.get("address_city", "")
    def_state = profile.get("address_state", "")
    def_zip = profile.get("address_zip", "")

    with st.container(border=True):
        st.subheader("📍 Addressing")
        c_to, c_from = st.columns(2)
        with c_to:
            st.markdown("#### 👉 To (Recipient)")
            st.text_input("Full Name", key="to_name")
            st.text_input("Street Address", key="to_street")
            r1, r2, r3 = st.columns([2, 1, 1])
            r1.text_input("City", key="to_city")
            r2.text_input("State", key="to_state")
            r3.text_input("Zip", key="to_zip")
        with c_from:
            st.markdown("#### 👈 From (You)")
            name = st.text_input("Your Name", value=def_name, key="from_name")
            street = st.text_input("Street Address", value=def_street, key="from_street")
            s1, s2, s3 = st.columns([2, 1, 1])
            city = s1.text_input("City", value=def_city, key="from_city")
            state = s2.text_input("State", value=def_state, key="from_state")
            zip_code = s3.text_input("Zip", value=def_zip, key="from_zip")
            if st.button("💾 Save My Address"):
                if database and user_email:
                    database.update_user_profile(user_email, name, street, city, state, zip_code)
                    st.toast("✅ Saved!")
        
    st.write("---")
    
    c_sig, c_mic = st.columns(2)
    with c_sig:
        st.write("✍️ **Signature**")
        st_canvas(
            stroke_width=2,
            stroke_color="#000000",
            background_color="#ffffff",
            height=150, 
            width=400,
            key="canvas"
        )
    
    with c_mic:
        st.write("🎤 **Dictation**")
        
        with st.expander("ℹ️ **How to Record**", expanded=True):
            st.write("1. Click the **Microphone**. 2. Speak. 3. Click **Red Square** to stop.")
            
        audio = st.audio_input("Record Message")
        
        if audio:
            # FIXED: Better status messaging so you know if it's loading or frozen
            with st.status("🤖 AI Status", expanded=True) as status:
                st.write("1. Uploading audio...")
                if ai_engine:
                    st.write("2. Loading AI Model (This may take 10s)...")
                    text = ai_engine.transcribe_audio(audio)
                    
                    if "Error" in text:
                        status.update(label="❌ Failed", state="error")
                        st.error(text)
                    else:
                        st.write("3. Cleaning text...")
                        status.update(label="✅ Complete!", state="complete")
                        st.session_state.transcribed_text = text
                        st.session_state.app_mode = "review"
                        st.rerun()

def render_review_page():
    render_hero("Review Letter", "Finalize and send")
    st.text_area("Body", st.session_state.get("transcribed_text", ""), height=300)
    if st.button("🚀 Send", type="primary", use_container_width=True):
        st.success("Sent!")
        if st.button("Finish"):
            st.session_state.clear()
            st.rerun()