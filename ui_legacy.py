import streamlit as st
import time

# --- ROBUST IMPORTS ---
import streamlit as st

# --- SAFE IMPORTS ---
try:
    import database
except Exception:
    database = None

try:
    import payment_engine
except Exception:
    payment_engine = None

# Add any other imports you see on line 5-10 here, 
# ensuring "try" and "except" are on different lines.
def render_legacy_page():
    # --- 1. THEME & STYLING (Gold/Serif) ---
    st.markdown("""
        <style>
        .legacy-header {
            font-family: 'Georgia', serif;
            color: #8B7355; /* Antique Bronze */
            text-align: center;
            padding-bottom: 20px;
        }
        .legacy-container {
            background-color: #FAF9F6; /* Off-white */
            padding: 30px;
            border-radius: 15px;
            border: 1px solid #E0DACC;
        }
        .stButton>button {
            background-color: #8B7355 !important;
            color: white !important;
            border: none;
            font-family: 'Georgia', serif;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. AUTH GUARD ---
    if not st.session_state.get('authenticated'):
        st.markdown("<h1 class='legacy-header'>🕯️ The Legacy Letter</h1>", unsafe_allow_html=True)
        st.info("🔒 This service requires a secure account. Please log in.")
        if st.button("Log In / Sign Up"):
             st.query_params["view"] = "login"
             st.rerun()
        return

    # --- 3. HEADER ---
    st.markdown("<h1 class='legacy-header'>The Forever Letter</h1>", unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align: center; font-style: italic; color: #666; margin-bottom: 30px;">
    "To be read when I am gone, or when you need me most."
    </div>
    """, unsafe_allow_html=True)

    # --- 4. CONTEXT & PROMPTS ---
    with st.container(border=True):
        st.subheader("1. The Recipient")
        recipient_type = st.selectbox(
            "Who are you writing to?",
            ["My Spouse/Partner", "My Children", "My Grandchildren", "An Old Friend", "Ethical Will (To Everyone)"]
        )
        
        # Dynamic Prompts
        prompts = {
            "My Spouse/Partner": "What is your favorite memory of us? What do you hope for them after you're gone?",
            "My Children": "What is the most important lesson you learned in life? What are you proud of in them?",
            "My Grandchildren": "What was the world like when you were young? What advice do you have for their future?",
            "An Old Friend": "Share a shared memory that still makes you smile. What does their friendship mean to you?",
            "Ethical Will (To Everyone)": "What are your values? What traditions do you want kept alive?"
        }
        st.info(f"💡 **Reflection Prompt:** {prompts.get(recipient_type)}")

    # --- 5. RECORDING ---
    st.write("")
    with st.container(border=True):
        st.subheader("2. Capture Your Voice")
        audio_val = st.audio_input("Record Message")
        
        if audio_val and ai_engine:
            if st.button("Transcribe & Polish"):
                with st.spinner("Transcribing..."):
                    # Transcribe
                    import tempfile, os
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as t:
                        t.write(audio_val.getvalue())
                        tpath = t.name
                    
                    try:
                        raw = ai_engine.transcribe_audio(tpath)
                        # Legacy Auto-Polish (Professional/Heartfelt)
                        polished = ai_engine.refine_text(raw, "Professional") 
                        st.session_state.legacy_text = polished
                    except Exception as e:
                        st.error(f"Error: {e}")
                    finally:
                        try: os.remove(tpath)
                        except: pass
                    st.rerun()

    # --- 6. EDITING ---
    if "legacy_text" not in st.session_state:
        st.session_state.legacy_text = ""

    st.write("")
    with st.container(border=True):
        st.subheader("3. Review")
        final_text = st.text_area("Your Words", st.session_state.legacy_text, height=300)
        st.session_state.legacy_text = final_text

    # --- 7. CHECKOUT ---
    st.write("")
    if st.button("Sealed & Delivered ($15.99)", type="primary", use_container_width=True):
        if not final_text:
            st.error("Please record or write your letter first.")
        else:
            # 1. Save Draft
            if database:
                user = st.session_state.get("user_email")
                d_id = database.save_draft(user, final_text, "Legacy", 15.99)
                st.session_state.current_draft_id = d_id
            
            # 2. Payment Link
            if payment_engine:
                base = "https://verbapost.streamlit.app"
                if secrets_manager:
                    base = secrets_manager.get_secret("BASE_URL") or base
                
                success_url = f"{base.rstrip('/')}?session_id={{CHECKOUT_SESSION_ID}}&tier=Legacy"
                
                url, sid = payment_engine.create_checkout_session(
                    "VerbaPost Legacy Service",