import streamlit as st
import time
import ui_login
import ui_advisor
import ui_heirloom
import ui_admin
import ui_splash
import ui_legal 

# --- IMPORTS FOR AUTH ---
try: import auth_engine
except ImportError: auth_engine = None
try: import database
except ImportError: database = None
try: import payment_engine # <--- Added Import
except ImportError: payment_engine = None

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="VerbaPost",
    page_icon="📬",
    layout="centered",
    initial_sidebar_state="collapsed" 
)

def handle_logout():
    """Clear session and reload to home."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.query_params.clear()
    st.rerun()

def main():
    # 1. INITIALIZE STATE
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user_role" not in st.session_state:
        st.session_state.user_role = "user"
    if "user_email" not in st.session_state:
        st.session_state.user_email = None

    query_params = st.query_params

    # 1.5 🚨 CRITICAL: PAYMENT RETURN HANDLER 🚨
    # Checks for Stripe redirect BEFORE requiring login.
    # This fixes the "Logged Out / No Credit" issue.
    if "session_id" in query_params:
        session_id = query_params["session_id"]
        if payment_engine:
            with st.spinner("Verifying Payment..."):
                success, msg = payment_engine.handle_payment_return(session_id)
                if success:
                    st.toast(f"Payment Confirmed: {msg}!", icon="✅")
                    # Optional: Clean URL so a refresh doesn't re-trigger (though idempotency handles it)
                    st.success("✅ Credit Added to your account! Please log in to view.")
                    time.sleep(2)
                    # We do NOT return here; we let them fall through to Login
                else:
                    if msg != "Already Fulfilled":
                        st.error(f"Payment Verification Failed: {msg}")
        
        # Clean URL to prevent confusion
        # st.query_params.clear() # Optional: Keep session_id visible for debugging or clear it

    # 2. 🚨 PUBLIC PLAYBACK GATE (QR Code Bypass) 🚨
    if "play" in query_params:
        audio_id = query_params["play"]
        if ui_heirloom and hasattr(ui_heirloom, 'render_public_player'):
            ui_heirloom.render_public_player(audio_id)
            return
        else:
            st.error("⚠️ Player module (ui_heirloom) is missing or incomplete.")
            return

    # 3. HANDLE GOOGLE CALLBACK
    if "code" in query_params and not st.session_state.authenticated:
        if auth_engine:
            try:
                with st.spinner("🔄 Verifying Google Login..."):
                    user, error = auth_engine.handle_google_callback(query_params["code"])
                    if user:
                        st.session_state.authenticated = True
                        st.session_state.user_email = user.email
                        if database:
                            profile = database.get_user_profile(user.email)
                            if profile:
                                st.session_state.user_role = profile.get("role", "user")
                        st.success(f"✅ Logged in as {user.email}")
                        time.sleep(1)
                        st.query_params.clear()
                        st.rerun()
                    else:
                        st.error(f"❌ Google Auth Failed: {error}")
                        if st.button("Try Logging in Again"):
                            st.query_params.clear()
                            st.rerun()
            except Exception as e:
                st.error(f"⚠️ Auth System Error: {e}")

    # 4. 🛠️ GLOBAL SIDEBAR 🛠️
    with st.sidebar:
        st.header("VerbaPost Admin")
        
        if st.session_state.authenticated:
            st.success(f"🟢 Online: {st.session_state.user_email}")
            st.caption(f"Role: {st.session_state.user_role}")
            
            user_email = st.session_state.user_email
            is_admin = (
                (st.session_state.user_role == "admin") or 
                (user_email == "tjkarat@gmail.com") or 
                (user_email == "tjkarat@gmai.com") or
                (user_email == "pat@gmail.com")
            )
            
            if is_admin:
                st.divider()
                st.subheader("🕵️ Role Switcher")
                if st.button("⚙️ Admin Console"): 
                    st.session_state.user_role = "admin"
                    st.rerun()
                if st.button("👔 Advisor View"): 
                    st.session_state.user_role = "advisor"
                    st.rerun()
                if st.button("📂 Heir View"): 
                    st.session_state.user_role = "heir"
                    st.rerun()
            
            st.divider()
            if st.button("🚪 Log Out"):
                handle_logout()
        else:
            st.warning("🔴 Not Logged In")
            st.info("Please sign in to access tools.")
            if st.button("Reset Session"):
                handle_logout()

    # 5. ROUTING LOGIC
    nav = query_params.get("nav")
    
    # Compatibility Bridge
    if not nav and st.session_state.get("app_mode") == "login":
        nav = "login"

    # --- AUTHENTICATED ROUTES ---
    if st.session_state.authenticated:
        role = st.session_state.user_role
        
        # Dual Role / Force Heir View
        force_heir = ("pending_play_id" in st.session_state) or (nav == "archive")
        
        if force_heir:
            if ui_heirloom: ui_heirloom.render_family_archive()
            else: st.error("Heirloom UI missing")
            return

        # Role Routing
        if role == "advisor":
            if ui_advisor: ui_advisor.render_advisor_portal()
            else: st.error("Advisor UI missing")
        
        elif role == "admin":
            if ui_admin: ui_admin.render_admin_console()
            else: st.error("Admin UI missing")
                
        else: # Default/Heir
            if ui_heirloom: ui_heirloom.render_family_archive()
            else: st.error("Heirloom UI missing")
        return

    # --- PUBLIC ROUTES ---
    if nav == "login" or nav == "advisor":
        if ui_login: ui_login.render_login_page()
        else: st.error("Login UI missing")
        
    elif nav == "archive":
        if ui_login: ui_login.render_login_page()
        else: st.error("Login UI missing")

    # --- 🆕 RESTORED LEGAL ROUTE ---
    elif nav == "legal":
        if ui_legal: ui_legal.render_legal_page()
        else: st.error("Legal UI missing")

    else:
        # Default: The Marketing Splash Page
        if ui_splash and hasattr(ui_splash, 'render_splash_page'):
            ui_splash.render_splash_page()
        elif ui_splash and hasattr(ui_splash, 'render_splash'):
            ui_splash.render_splash()
        else:
            st.title("VerbaPost")
            if st.button("Go to Login"):
                st.query_params["nav"] = "login"
                st.rerun()

if __name__ == "__main__":
    main()