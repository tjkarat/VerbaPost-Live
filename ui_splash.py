import streamlit as st

# Version 13.0 - No f-strings (Guaranteed Syntax Fix)
def show_splash():
    # --- CONFIG ---
    P_STANDARD = ".99"
    P_HEIRLOOM = ".99"
    P_CIVIC = ".99"

    # --- HERO ---
    st.title("VerbaPost 📮")
    st.subheader("The Authenticity Engine.")
    st.markdown("##### Texts are trivial. Emails are ignored. Real letters get read.")
    
    st.divider()

    # --- HOW IT WORKS ---
    c1, c2, c3 = st.columns(3)
    with c1:
        st.info("🎙️ **1. Dictate**")
        st.caption("Tap the mic. AI handles the typing.")
    with c2:
        st.warning("✍️ **2. Sign**")
        st.caption("Review the text, sign on screen.")
    with c3:
        st.success("📮 **3. We Mail**")
        st.caption("We print, stamp, and mail it.")

    st.divider()

    # --- PRICING TIERS ---
    st.subheader("Simple Pricing")
    
    # PURE STRING - NO f-string, NO variables
    css = """
    <style>
        .price-card {
            background-color: #f9f9f9;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            border: 1px solid #ddd;
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .price-tag {
            color: #E63946;
            font-size: 32px;
            font-weight: bold;
            margin: 10px 0;
        }
        .price-title {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 5px;
            color: #333;
        }
        .price-desc {
            font-size: 14px;
            color: #666;
            line-height: 1.4;
        }
        .grid-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }
    </style>
    """

    # CONCATENATION - Impossible to break syntax
    html_content = """
    <div class="grid-container">
        <div class="price-card">
            <div>
                <div class="price-title">⚡ Standard</div>
                <div class="price-tag">""" + P_STANDARD + """</div>
                <div class="price-desc">API Fulfillment<br>Window Envelope<br>Mailed in 24hrs</div>
            </div>
        </div>

        <div class="price-card" style="border: 2px solid #4CAF50; background-color: #f0fff4;">
            <div>
                <div class="price-title">🏺 Heirloom</div>
                <div class="price-tag">""" + P_HEIRLOOM + """</div>
                <div class="price-desc">Hand-Stamped<br>Premium Paper<br>Mailed from Nashville</div>
            </div>
        </div>

        <div class="price-card">
            <div>
                <div class="price-title">🏛️ Civic Blast</div>
                <div class="price-tag">""" + P_CIVIC + """</div>
                <div class="price-desc">Activism Mode<br>Auto-Find Reps<br>Mails Senate + House</div>
            </div>
        </div>
    </div>
    """
    
    st.markdown(css + html_content, unsafe_allow_html=True) 

    st.divider()

    # --- CTA ---
    col_spacer, col_btn, col_spacer2 = st.columns([1, 2, 1])
    with col_btn:
        if st.button("🚀 Create My Account", type="primary", use_container_width=True):
            st.session_state.current_view = "login"
            st.session_state.initial_mode = "signup"
            st.rerun()
        
        st.write("")
        
        if st.button("Already a member? Log In", type="secondary", use_container_width=True):
            st.session_state.current_view = "login"
            st.session_state.initial_mode = "login"
            st.rerun()
