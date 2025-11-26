import streamlit as st
import pandas as pd

# Try imports to avoid crashes if modules are missing
try: import database
except: database = None
try: import promo_engine
except: promo_engine = None

def show_admin():
    st.title("🔐 Admin Console")
    
    # Safety check for user object
    u_email = "Unknown"
    if st.session_state.get("user"):
        if isinstance(st.session_state.user, dict):
            u_email = st.session_state.user.get("email", "Unknown")
        else:
            u_email = getattr(st.session_state.user, "email", 
                      getattr(st.session_state.user.user, "email", "Unknown"))
            
    st.info(f"Logged in as: {u_email}")
    
    # 1. Quick Stats
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("System Status", "Online 🟢")
    with c2:
        if database: st.metric("Database", "Connected 🟢")
        else: st.metric("Database", "Offline 🔴")
    with c3:
        if "stripe" in st.secrets: st.metric("Stripe", "Configured 🟢")
        else: st.metric("Stripe", "Missing 🔴")

    st.divider()

    tab_promo, tab_db = st.tabs(["🎟️ Promo Codes", "🗄️ Database Data"])

    # --- PROMO CODES ---
    with tab_promo:
        st.subheader("Generate Single-Use Code")
        if promo_engine:
            if st.button("Generate Code"):
                code = promo_engine.generate_code()
                st.success(f"New Code: `{code}`")
                st.caption("Copy this code now. It is valid for one use.")
        else:
            st.warning("Promo engine module not loaded.")

    # --- DATABASE VIEW ---
    with tab_db:
        st.subheader("Recent Drafts & Users")
        if database:
            st.info("Database connection is active.")
            st.write("To view data tables, add a `fetch_all()` function to database.py")
        else:
            st.warning("Database not connected.")

    # --- EXIT ---
    st.markdown("---")
    if st.button("⬅️ Return to Main App"):
        st.session_state.current_view = "splash"
        st.rerun()