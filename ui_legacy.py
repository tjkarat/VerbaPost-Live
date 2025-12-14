import streamlit as st
import time

# --- ROBUST IMPORTS ---
try:
    import database
except Exception:
    database = None

try:
    import payment_engine
except Exception:
    payment_engine = None

try:
    import secrets_manager
except Exception:
    secrets_manager = None

try:
    import letter_format
except Exception:
    letter_format = None

# --- LEGACY PAGE LOGIC ---
def render_legacy_page():
    st.markdown("## 🕊️ Legacy Service (End of Life)")
    st.info("Securely document and deliver your final wishes. No AI processing. 100% Private.")

    # --- 1. SENDER INFO ---
    with st.expander("📍 Step 1: Your Information", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Your Name", key="leg_name")
            street = st.text_input("Street Address", key="leg_street")
        with c2:
            city = st.text_input("City", key="leg_city")
            state = st.text_input("State", key="leg_state")
            zip_code = st.text_input("Zip", key="leg_zip")

    # --- 2. COMPOSITION (NO AI) ---
    st.markdown("### ✍️ Step 2: Compose Letter")
    
    # Font Selection with Visual Cues
    st.write("Choose a handwriting style for your letter:")
    font_cols = st.columns(4)
    
    # Using session state to track font choice
    if "legacy_font" not in st.session_state:
        st.session_state.legacy_font = "Caveat"

    # Radio button hidden functionality via visual columns
    font_choice = st.radio(
        "Select Font Style:",
        ["Caveat", "Great Vibes", "Indie Flower", "Schoolbell"],
        horizontal=True,
        index=0,
        help="Select the handwriting style for the PDF."
    )
    st.session_state.legacy_font = font_choice

    # Large Text Area for Long Files
    st.markdown(f"**Selected Style:** *{font_choice}*")
    letter_text = st.text_area(
        "Type your message here (Unlimited length):", 
        height=600, 
        placeholder="My dearest family,\n\nI am writing this to share my final thoughts...",
        help="This text is processed locally and formatted directly into PDF. No AI analysis is performed."
    )

    # Optional File Upload for Text
    uploaded_text = st.file_uploader("Or upload a text file (.txt)", type=["txt"])
    if uploaded_text:
        letter_text = uploaded_text.read().decode("utf-8")
        st.success("File loaded successfully!")

    # --- 3. PREVIEW & PAY ---
    st.markdown("### 👁️ Step 3: Preview & Secure")
    
    col_prev, col_pay = st.columns([1, 1])

    with col_prev:
        if st.button("📄 Generate PDF Preview"):
            if not name or not letter_text:
                st.error("Please fill in your name and letter text first.")
            elif letter_format:
                # Create dummy sender/recipient for preview
                s_data = {"name": name, "street": street, "city": city, "state": state, "zip": zip_code}
                r_data = {"name": "Recipient Name", "street": "123 Example St", "city": "City", "state": "ST", "zip": "00000"}
                
                pdf_bytes = letter_format.create_pdf(
                    letter_text, 
                    s_data, 
                    r_data, 
                    tier="Legacy",
                    font_choice=st.session_state.legacy_font
                )
                st.download_button(
                    label="⬇️ Download PDF Proof",
                    data=pdf_bytes,
                    file_name="legacy_proof.pdf",
                    mime="application/pdf"
                )
            else:
                st.error("PDF Engine not loaded.")

    with col_pay:
        st.markdown(f"""
        **Total: $15.99**
        * Archival Paper
        * Certified Mail Tracking
        * {font_choice} Handwriting Style
        """)
        
        if st.button("💳 Proceed to Payment ($15.99)", type="primary"):
            if payment_engine:
                base = "https://verbapost.streamlit.app"
                if secrets_manager:
                    sec_url = secrets_manager.get_secret("BASE_URL")
                    if sec_url: base = sec_url
                
                success_url = f"{base.rstrip('/')}?session_id={{CHECKOUT_SESSION_ID}}&tier=Legacy&service=EndOfLife"
                
                url, sid = payment_engine.create_checkout_session(
                    f"Legacy Letter ({font_choice})",
                    1599,
                    success_url,
                    base
                )
                if url:
                    st.link_button("👉 Secure Checkout", url)
            else:
                st.error("Payment system offline.")

    st.markdown("---")
    if st.button("⬅️ Return to Main App"):
        st.query_params.clear()
        st.rerun()