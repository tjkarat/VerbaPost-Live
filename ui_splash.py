import streamlit as st

def render_splash_page():
    # --- HERO SECTION ---
    st.markdown("""
        <div style='text-align: center; padding: 40px 0;'>
            <h1 style='font-family: "Helvetica Neue", serif; font-size: 3rem; font-weight: 700; color: #1f2937;'>
                VerbaPost Wealth
            </h1>
            <p style='font-size: 1.2rem; color: #4b5563; max-width: 600px; margin: 0 auto;'>
                The high-touch client retention platform for independent financial advisors.
            </p>
        </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("""
        <div style="background: #f8fafc; padding: 20px; border-radius: 10px; border: 1px solid #e2e8f0; text-align: left;">
            <h3 style="margin-top: 0;"> The Retention Package</h3>
            <ul style="font-size: 1.1rem; line-height: 1.6;">
                <li>🎙️ <b>AI-Driven Client Interviews:</b> We capture their family stories & legacy goals.</li>
                <li>📝 <b>Physical Deliverables:</b> We mail beautiful transcripts to them (and you).</li>
                <li>🛡️ <b>Compliance First:</b> You approve every word before it prints.</li>
            </ul>
        </div>
        <br>
        """, unsafe_allow_html=True)

        if st.button("🔒 Advisor Login / Portal Access", type="primary", use_container_width=True):
            st.session_state.app_mode = "login"
            st.rerun()

    st.markdown("<br><br><hr>", unsafe_allow_html=True)
    st.caption("© 2026 VerbaPost Wealth Management Solutions. Restricted Access.")