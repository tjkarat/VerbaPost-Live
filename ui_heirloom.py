import streamlit as st
import database
from datetime import datetime

def render_dashboard():
    """
    The Main Heirloom Dashboard.
    This replaces the standard 'Store' view for Heirloom subscribers.
    """
    
    # 1. GET USER DATA
    user_email = st.session_state.get("user_email")
    if not user_email:
        st.error("Please log in.")
        return

    # Fetch the full profile to get parent_name, parent_phone, etc.
    # Note: We assume database.get_user_profile(email) returns a dict or object
    # If not, we might need to add a helper in database.py
    user = database.get_user_profile(user_email)
    
    # 2. HEADER
    st.markdown("## 🕰️ The Family Archive")
    
    if not user:
        st.error("User profile not found.")
        return

    # 3. TABS
    tab_overview, tab_stories, tab_settings = st.tabs(["🏠 Overview", "📖 Stories", "⚙️ Settings"])

    # --- TAB: OVERVIEW ---
    with tab_overview:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.info(f"Welcome back, {user.first_name}. Your Story Line is active.")
            st.markdown(
                """
                ### 📞 How it works
                1. **Tell Mom to call:** `(615) 555-0199` (Example Number)
                2. **She talks:** We record her story.
                3. **You review:** You'll see the text here. Edit it, then click 'Print'.
                """
            )
        with col2:
            st.metric("Stories Captured", "0")
            st.metric("Next Letter Due", "Jan 15")

    # --- TAB: STORIES (The Inbox) ---
    with tab_stories:
        st.write("### 📥 Incoming Stories")
        # Placeholder for now - eventually we list database rows here
        st.markdown("*No stories recorded yet.*")
        
        # --- MANUAL UPLOAD (For your testing) ---
        st.markdown("---")
        with st.expander("🛠️ Admin: Upload Audio Manually"):
            uploaded_file = st.file_uploader("Upload MP3/WAV", type=['mp3', 'wav', 'm4a'])
            if uploaded_file and st.button("Transcribe & Save"):
                st.warning("⚠️ Integration with AI Engine coming in Step 2!")

    # --- TAB: SETTINGS ---
    with tab_settings:
        st.write("### 👵 Parent Details")
        with st.form("heirloom_setup"):
            # Pre-fill with existing data if we have it
            current_parent = getattr(user, 'parent_name', '') or ""
            current_phone = getattr(user, 'parent_phone', '') or ""

            p_name = st.text_input("Parent's Name", value=current_parent, placeholder="e.g. Grandma Mary")
            p_phone = st.text_input("Parent's Phone Number", value=current_phone, placeholder="e.g. +1615...")
            
            if st.form_submit_button("Save Details"):
                # We need to add this function to database.py next!
                success = database.update_heirloom_profile(user_email, p_name, p_phone)
                if success:
                    st.success("Saved!")
                    st.rerun()
                else:
                    st.error("Database update failed.")
