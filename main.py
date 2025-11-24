import streamlit as st
import sys

# 1. Setup Page
print("--- STARTING APP ---")
st.set_page_config(page_title="VerbaPost", layout="wide")
print("Step 1: Config set")

# 2. Inject Styles
st.markdown("""
    <style>
    .block-container {padding-top: 2rem;}
    </style>
    """, unsafe_allow_html=True)

# 3. Load Modules (With explicit debugging)
try:
    print("Step 2: Importing modules...")
    import ui_splash
    print(" - ui_splash loaded")
    import ui_login
    print(" - ui_login loaded")
    import auth_engine
    print(" - auth_engine loaded")
    import ui_main
    print(" - ui_main loaded")
    import ui_admin
    print(" - ui_admin loaded")
    import ui_legal
    print(" - ui_legal loaded")
except Exception as e:
    print(f"CRITICAL IMPORT ERROR: {e}")
    st.error(f"🔥 Critical Error: {e}")
    st.stop()

# 4. Session State
if "current_view" not in st.session_state:
    st.session_state.current_view = "splash"

# 5. Router
view = st.session_state.current_view
print(f"Step 3: Rendering view '{view}'")

if view == "splash":
    ui_splash.show_splash()
elif view == "login":
    # Pass the functions directly from auth_engine
    ui_login.show_login(auth_engine.sign_in, auth_engine.sign_up)
elif view == "main_app":
    ui_main.show_main_app()
elif view == "admin":
    ui_admin.show_admin()
elif view == "legal":
    ui_legal.show_legal()
else:
    st.write("Unknown view")

print("--- RENDER COMPLETE ---")