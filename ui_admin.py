import streamlit as st
import pandas as pd

# Try imports to avoid crashes if modules are missing
try: import database
except: database = None
try: import promo_engine
except: promo_engine = None

def show_admin():
    st.title("🔐 Admin Console")
    st.info(f"Logged in as: {st.session_state.user.email}")
    
    # 1. Quick Stats
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("System Status", "Online 🟢")
    with c2:
        if database: st.metric("Database", "Connected 🟢")
        else: st.metric("Database", "Offline 🔴")
    with c3:
        if "stripe" in st.secrets: st.metric("Stripe Keys", "Loaded 🟢")
        else: st.metric("Stripe Keys", "Missing 🔴")

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
        st.subheader("Recent Activity")
        if database:
            st.info("Database connection is active.")
            # Placeholder: In the future, you can add database.get_all_users() here
            st.write("To view data tables, add a fetch function to database.py")
        else:
            st.warning("Database not connected.")

    # --- EXIT ---
    st.markdown("---")
    if st.button("⬅️ Return to Main App"):
        st.session_state.app_mode = "splash"
        st.rerun()