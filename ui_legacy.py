import streamlit as st
import ui_login
import ai_engine
import pricing_engine
import database
import payment_engine
import time

def render_legacy_page():
    # 1. Theme Setting (Solemn/Gold)
    st.markdown("""
        <style>
        .legacy-header {
            font-family: 'Georgia', serif;
            color: #8B7355; /* Antique Bronze */
            text-align: center;
            padding-bottom: 20px;
        }
        .security-badge {
            background-color: #f0f2f6;
            border-left: 5px solid #8B7355;
            padding: 15px;
            margin-top: 20px;
            font-size: 0.9em;
            color: #555;
        }
        .stButton>button {
            background-color: #8B7355 !important;
            color: white !important;
            border: none;
        }
        </style>
    """, unsafe_allow_html=True)

    # 2. Authentication Gate
    if not st.session_state.get('authenticated'):
        st.markdown("<h1 class='legacy-header'>The Legacy Letter</h1>", unsafe_allow_html=True)
        st.info("🔒 Please sign in to access the secure Legacy vault.")
        
        if st.button("Log In to Continue"):
             st.session_state.auth_view = "login"
             st.rerun()
             
        # Render login inline
        ui_login.render_login()
        return

    # 3. Header & Promise
    st.markdown("<h1 class='legacy-header'>🕯️ The Forever Letter</h1>", unsafe_allow_html=True)
    st.markdown("""
    **This is not just mail.** This is a permanent artifact on archival cotton paper.
    
    * **Voice-First:** Speak from the heart. We handle the typing.
    * **Privacy First:** Once mailed, the digital copy is **permanently deleted**.
    * **Heirloom Quality:** 100-year archival paper.
    """)

    # 4. Context Selector (The "Writer's Block" Cure)
    st.write("---")
    st.subheader("1. Who is this for?")
    
    recipient_type = st.selectbox(
        "Choose a context to get helpful prompts:",
        ["My Spouse", "My Children", "My Grandchildren", "An Old Friend", "Apology / Reconciliation", "Instruction / Ethical Will"]
    )
    
    # Dynamic Prompts based on selection
    prompts = {
        "My Spouse": "What is your favorite memory of us? What do you hope for them after you're gone?",
        "My Children": "What is the most important lesson you learned in life? What are you proud of?",
        "My Grandchildren": "What was the world like when you were young? What advice do you have for their future?",
        "Apology / Reconciliation": "What do you regret? What do you want to forgive or be forgiven for?",
        "Instruction / Ethical Will": "What are your values? What traditions do you want kept alive?"
    }
    
    st.info(f"💡 **Prompt:** {prompts.get(recipient_type)}")

    # 5. Audio Recorder (Reuse AI Engine)
    st.write("---")
    st.subheader("2. Record Your Message")
    
    audio_value = st.audio_input("Press microphone to record")
    
    if audio_value:
        st.success("Audio captured. Transcribing securely on-device...")
        with st.spinner("Listening & Refining..."):
            # Reuse your existing robust AI engine
            raw_text = ai_engine.transcribe_audio(audio_value)
            
            # Auto-Polish for Legacy (Included in $15.99 price)
            final_text = ai_engine.refine_text(raw_text, style="Professional")
            
            st.session_state.legacy_text = final_text
            st.rerun()

    # 6. The Editor & Font Selector
    if "legacy_text" not in st.session_state:
        st.session_state.legacy_text = ""

    # Show editor if text exists OR user wants to type manually
    if st.session_state.legacy_text or st.button("Start writing manually instead"):
        st.write("---")
        st.subheader("3. Review & Style")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            edited_text = st.text_area("Your Letter", st.session_state.legacy_text, height=400)
            st.session_state.legacy_text = edited_text
            
        with col2:
            st.markdown("#### ✍️ Handwriting Style")
            font_choice = st.radio(
                "Choose an archetype:",
                ["The Executive", "The Poet", "The Teacher", "The Architect", "The Grandparent"]
            )
            st.session_state.legacy_font = font_choice
            
            st.markdown("#### 📜 Paper")
            st.caption("Cotton Archival Bond (Cream)")
            st.caption("Certified Tracking Included")

        # 7. The "Print & Purge" Checkout
        st.write("---")
        st.markdown("""
        <div class="security-badge">
            <b>🛡️ The Privacy Pledge:</b> By clicking below, you authorize VerbaPost to print this document. 
            Once carrier delivery is confirmed, <b>this digital file will be scrubbed from our database</b>.
        </div>
        """, unsafe_allow_html=True)
        
        # Calculate Price
        price = pricing_engine.calculate_total("Legacy", is_intl=False, is_certified=True)
        
        if st.button(f"Seal & Send (Legacy Tier - ${price})", type="primary"):
            # A. Guard: Check Auth again
            user_email = st.session_state.get("user_email")
            if not user_email:
                st.error("Session expired. Please log in.")
                st.stop()

            # B. Save Draft (The Ghost Draft Prevention)
            if database.save_draft: 
                d_id = st.session_state.get("current_draft_id")
                
                # If no draft exists, create one
                if not d_id:
                     d_id = database.save_draft(user_email, st.session_state.legacy_text, "Legacy", price)
                     st.session_state.current_draft_id = d_id
                else:
                     # Update existing
                     database.update_draft_data(d_id, 
                                                text=st.session_state.legacy_text, 
                                                tier="Legacy", 
                                                price=price, 
                                                status="Draft")

            # C. Lock Session Variables
            st.session_state.locked_tier = "Legacy"
            st.session_state.locked_price = price
            
            # D. Trigger Stripe
            payment_engine.create_checkout_session(
                price, 
                "Legacy", 
                st.session_state.get("current_draft_id", "legacy_temp"), 
                user_email
            )
