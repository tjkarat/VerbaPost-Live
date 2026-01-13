import streamlit as st
import time
from datetime import datetime

# --- MODULE IMPORTS ---
try: import database
except ImportError: database = None
try: import ai_engine
except ImportError: ai_engine = None
try: import heirloom_engine
except ImportError: heirloom_engine = None
try: import audit_engine
except ImportError: audit_engine = None

def render_dashboard():
    """
    The Family Archive Portal (Heir View).
    Streamlined for B2B: Edit -> Submit -> Wait for Advisor.
    """
    if not st.session_state.get("authenticated"):
        st.warning("Please log in."); return

    user_email = st.session_state.get("user_email")
    
    # 1. HEADER: BRANDING
    # We fetch projects to see who the advisor is
    projects = []
    if database:
        projects = database.get_heir_projects(user_email)
    
    firm_name = projects[0].get('firm_name') if projects else "VerbaPost"
    
    col_logo, col_title = st.columns([1, 4])
    with col_title:
        st.title("The Family Archive")
        st.caption(f"Sponsored by {firm_name} | Preserving your family legacy.")

    st.divider()

    # 2. TABS
    tab_inbox, tab_setup = st.tabs(["📥 Story Inbox", "⚙️ Setup & Interview"])

    # --- TAB A: INBOX (THE WORKFLOW) ---
    with tab_inbox:
        if not projects:
            st.info("No stories found yet. Use the 'Setup' tab to start an interview.")
        
        # Sort: Pending/Recording first, then Sent
        # Simple lambda sort logic if needed, but DB usually handles order
        
        for p in projects:
            pid = p.get('id')
            status = p.get('status', 'Recording')
            date_str = p.get('created_at', 'Unknown Date')
            content = p.get('content', '')
            
            # Status Badge Logic
            if status == "Pending Approval":
                icon = "⏳"
                badge_color = "orange"
                label = "Waiting for Advisor Review"
            elif status == "Approved" or status == "Sent":
                icon = "✅"
                badge_color = "green"
                label = "Preserved & Mailed"
            else:
                icon = "🎙️"
                badge_color = "blue"
                label = "Draft (Needs Editing)"

            with st.expander(f"{icon} {date_str} | {label}", expanded=(status=='Recording')):
                
                # STATUS BANNER
                st.markdown(f":{badge_color}[**Status: {label}**]")
                
                # EDITING AREA (Only editable if not yet approved)
                is_editable = (status == "Recording" or status == "Authorized")
                
                new_text = st.text_area(
                    "Transcript", 
                    value=content, 
                    height=250, 
                    key=f"txt_{pid}",