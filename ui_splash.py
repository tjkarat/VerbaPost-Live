import streamlit as st

def render_splash_page():
    """
    The 'App Portal' Entry Point.
    Replaces marketing fluff with clear Login pathways.
    UPDATED: Now uses URL params to drive routing in main.py.
    """
    # Simple, centered layout
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
            <div style='text-align: center; margin-top: 50px; margin-bottom: 30px;'>
                <h1 style='font-family: serif; color: #0f172a; font-size: 3rem;'>VerbaPost</h1>
                <p style='color: #64748b; font-size: 1.2rem; font-family: sans-serif;'>The Family Legacy Archive</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")

        # Two Clear Doors
        st.markdown("### Select Your Portal")
        
        tab_family, tab_advisor = st.tabs(["🏛️ For Families", "💼 For Advisors"])
        
        with tab_family:
            st.info("Access your private family vault to record and preserve stories.")
            # FIX: Set query param 'nav=login' so main.py sees it
            if st.button("🔐 Client Login", key="btn_heir_login", use_container_width=True):
                st.query_params["nav"] = "login"
                st.rerun()
                
        with tab_advisor:
            st.warning("Manage client rosters, credits, and activations.")
            # FIX: Set query param 'nav=advisor' so main.py sees it
            if st.button("💼 Advisor Login", key="btn_adv_login", use_container_width=True):
                st.query_params["nav"] = "advisor"
                st.rerun()
        
        st.markdown("---")
        
        # Subtle Footer
        st.markdown("""
            <div style='text-align: center; color: #94a3b8; font-size: 0.8rem; margin-top: 20px;'>
                Secure Bank-Grade Encryption • Archival Preservation Standards<br>
                © 2025 VerbaPost Wealth
            </div>
        """, unsafe_allow_html=True)

# Safety Alias
show_splash = render_splash_page