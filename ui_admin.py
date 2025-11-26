import streamlit as st
import pandas as pd

try: import database
except: database = None
try: import promo_engine
except: promo_engine = None

def show_admin():
    st.title("🔐 Admin Console")
    
    u_email = "Unknown"
    if st.session_state.get("user"):
        u = st.session_state.user
        if isinstance(u, dict): u_email = u.get("email", "Unknown")
        elif hasattr(u, "email"): u_email = u.email
        elif hasattr(u, "user"): u_email = u.user.email
            
    st.info(f"Logged in as: {u_email}")
    
    # 1. Stats
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("System", "Online 🟢")
    with c2: st.metric("Database", "Connected 🟢" if database else "Offline 🔴")
    with c3: st.metric("Stripe", "Configured 🟢" if "stripe" in st.secrets else "Missing 🔴")

    st.divider()
    tab_promo, tab_db = st.tabs(["🎟️ Promo Codes", "🗄️ Database Data"])

    with tab_promo:
        st.subheader("Generate Single-Use Code")
        if promo_engine:
            if st.button("Generate Code"):
                code = promo_engine.generate_code()
                st.success(f"New Code: `{code}`")
        else: st.warning("Promo engine not loaded.")

    with tab_db:
        st.subheader("Recent Letters")
        if database:
            # Call the new function
            data = database.fetch_all_drafts()
            if data:
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No drafts found in database.")
        else:
            st.warning("Database not connected.")

    st.markdown("---")
    if st.button("⬅️ Return to Main App"):
        st.session_state.current_view = "splash"
        st.rerun()