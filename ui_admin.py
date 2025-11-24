import streamlit as st

# --- SAFETY FIRST IMPORTS ---
# These try/except blocks prevent the "KeyError" crashes
try: import database
except ImportError: database = None

try: import ai_engine
except ImportError: ai_engine = None

try: import mailer
except ImportError: mailer = None

try: import analytics
except ImportError: analytics = None

def show_admin():
    st.title("🔐 Admin Console")
    
    # Visual Check of what is working
    st.subheader("🔌 System Diagnostics")
    
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        st.metric("Database", "✅ Connected" if database else "❌ Missing")
    with c2:
        st.metric("AI Engine", "✅ Loaded" if ai_engine else "❌ Error")
    with c3:
        st.metric("Mailer", "✅ Ready" if mailer else "❌ Missing")
    with c4:
        st.metric("Analytics", "✅ Active" if analytics else "❌ Missing")

    st.divider()
    
    tab1, tab2 = st.tabs(["📊 Overview", "⚙️ Config"])
    
    with tab1:
        if analytics:
            try:
                analytics.show_analytics()
            except Exception as e:
                st.error(f"Analytics module error: {e}")
        else:
            st.warning("Analytics.py file is missing or crashed.")

    with tab2:
        st.subheader("Secrets Debug")
        # Show safe version of secrets (keys masked)
        if "admin" in st.secrets:
            st.write("Admin Email configured:", st.secrets["admin"]["email"])
        elif "ADMIN_EMAIL" in st.secrets:
            st.write("Admin Email configured:", st.secrets["ADMIN_EMAIL"])
        else:
            st.error("No Admin Email found in Secrets!")