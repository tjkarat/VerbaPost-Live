import streamlit as st
import payment_engine
import auth_engine
import audit_engine
import ui_main
import ui_legacy
import ui_splash
import ui_login
import ui_admin
import database
import requests
import json
import letter_format
import email_engine
import secrets_manager

# --- CONFIGURATION ---
st.set_page_config(
    page_title="VerbaPost", 
    page_icon="📮", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# --- GLOBAL SIDEBAR ---
def render_sidebar():
    """
    Renders the Global Sidebar with Navigation, Admin Access, and Help.
    """
    with st.sidebar:
        # 1. Logo / Brand
        st.markdown("# 📮 VerbaPost")
        st.markdown("---")
        
        # 2. Navigation
        st.markdown("### 🧭 Navigation")
        if st.button("🏠 Home / Splash", use_container_width=True):
            st.session_state.app_mode = "splash"
            st.rerun()
            
        if st.button("🔐 Login / Account", use_container_width=True):
            st.session_state.app_mode = "login"
            st.rerun()

        # 3. Admin Access (RBAC Protected)
        user_email = st.session_state.get("user_email", "")
        # Add your admin email(s) here
        admin_emails = ["admin@verbapost.com", "tjkarat@gmail.com"]
        
        if st.session_state.get("authenticated") and user_email in admin_emails:
            st.markdown("---")
            st.markdown("### 🛡️ Admin")
            if st.button("⚙️ Admin Console", use_container_width=True):
                st.session_state.app_mode = "admin"
                st.rerun()

        # 4. Session Info / Debug
        if st.session_state.get("authenticated"):
            st.markdown("---")
            st.success(f"Logged in as:\n{user_email}")
            if st.button("Logout", use_container_width=True):
                st.session_state.authenticated = False
                st.session_state.user_email = ""
                st.session_state.app_mode = "splash"
                st.rerun()
        
        st.markdown("---")
        st.info("Support: support@verbapost.com")

def process_legacy_fulfillment(draft_id, user_email):
    """
    1. Generates PDF from Draft
    2. Sends to Postgrid (Certified)
    3. Emails Confirmation
    Returns: (success, tracking_number_or_id)
    """
    try:
        # A. Fetch Data
        with database.get_db_session() as db:
            draft = db.query(database.LetterDraft).filter(database.LetterDraft.id == draft_id).first()
            if not draft: return False, "Draft Not Found"
            
            content = draft.transcription
            to_addr = json.loads(draft.recipient_json) if draft.recipient_json else {}
            from_addr = json.loads(draft.sender_json) if draft.sender_json else {}
            # Try to get signature from sender json or default to name
            sig_text = draft.signature_data if hasattr(draft, 'signature_data') else None

        # B. Generate PDF
        pdf_bytes = letter_format.create_pdf(
            content, to_addr, from_addr, tier="Legacy", 
            font_choice="Caveat", signature_text=sig_text
        )

        # C. Send to Postgrid
        api_key = secrets_manager.get_secret("postgrid.api_key")
        if not api_key: return False, "Missing API Key"

        # Construct Postgrid Payload
        files = {
            'pdf': ('letter.pdf', pdf_bytes, 'application/pdf')
        }
        data = {
            'to': json.dumps({
                'firstName': to_addr.get('name', '').split(' ')[0],
                'lastName': ' '.join(to_addr.get('name', '').split(' ')[1:]),
                'addressLine1': to_addr.get('street'),
                'city': to_addr.get('city'),
                'state': to_addr.get('state'),
                'postalOrZip': to_addr.get('zip'),
                'countryCode': 'US'
            }),
            'from': json.dumps({
                'firstName': from_addr.get('name', '').split(' ')[0],
                'lastName': ' '.join(from_addr.get('name', '').split(' ')[1:]),
                'addressLine1': from_addr.get('street'),
                'city': from_addr.get('city'),
                'state': from_addr.get('state'),
                'postalOrZip': from_addr.get('zip'),
                'countryCode': 'US'
            }),
            'certified': 'true', # CRITICAL FOR LEGACY
            'description': f"Legacy Letter #{draft_id}"
        }

        # Send Request
        res = requests.post(
            "https://api.postgrid.com/print-mail/v1/letters",
            auth=(api_key, ''),
            data=data,
            files=files
        )
        
        if res.status_code in [200, 201]:
            res_json = res.json()
            # Postgrid returns 'id'. Tracking numbers often come later or are in metadata.
            # We use the Letter ID as reference if tracking is pending.
            tracking_ref = res_json.get('id') 
            
            # Update DB with Postgrid ID
            database.update_draft_data(draft_id, status="FULFILLED")
            
            # D. Send Email
            email_engine.send_confirmation(
                user_email, 
                tracking_number=tracking_ref, 
                tier="Legacy Certified"
            )
            return True, tracking_ref
            
        else:
            audit_engine.log_event(user_email, "POSTGRID_FAIL", str(draft_id), res.text)
            return False, f"Mailing Error: {res.text}"

    except Exception as e:
        audit_engine.log_event(user_email, "FULFILLMENT_EXCEPTION", str(draft_id), str(e))
        return False, str(e)

def main():
    # 1. Initialize Global Session State
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user_email" not in st.session_state:
        st.session_state.user_email = ""
    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "splash"

    # 2. Render Global Sidebar
    render_sidebar()

    # 3. Handle URL Parameters (Routing)
    query_params = st.query_params
    
    # A. Handle Payment Return (Stripe Redirect)
    session_id = query_params.get("session_id", None)
    
    # Only verify if we haven't already processed this session
    if session_id and session_id != st.session_state.get("last_processed_session"):
        with st.spinner("Verifying secure payment..."):
            # Verify with Stripe
            result = payment_engine.verify_session(session_id)
            
            if result and result.get("paid"):
                st.session_state.last_processed_session = session_id
                
                # CAPTURE EMAIL
                payer_email = result.get("email")
                if payer_email:
                    st.session_state.user_email = payer_email

                # RECOVER DRAFT ID (Critical Fix for Redirection Memory Loss)
                # If session state is lost, find the most recent pending draft for this user
                draft_id = st.session_state.get("current_legacy_draft_id")
                
                if not draft_id and payer_email:
                     # Attempt recovery from DB
                     with database.get_db_session() as db:
                         # Find recent draft (Legacy tier, not completed yet)
                         recent = db.query(database.LetterDraft).filter(
                             database.LetterDraft.user_email == payer_email,
                             database.LetterDraft.tier == 'Legacy',
                             database.LetterDraft.status != 'FULFILLED'
                         ).order_by(database.LetterDraft.created_at.desc()).first()
                         if recent:
                             draft_id = recent.id
                             # Update session to match recovered draft
                             st.session_state.current_legacy_draft_id = recent.id
                             st.session_state.legacy_text = recent.transcription

                # AUTOMATE FULFILLMENT
                if draft_id:
                    # Update status first
                    database.update_draft_data(draft_id, status="Paid", price=15.99)
                    
                    # Trigger Postgrid & Email
                    success, tracking_ref = process_legacy_fulfillment(draft_id, st.session_state.user_email)
                    
                    if success:
                        st.session_state.tracking_number = tracking_ref
                        st.session_state.paid_success = True
                        st.session_state.app_mode = "legacy" # FORCE LEGACY VIEW
                        st.success("✅ Payment & Fulfillment Complete!")
                    else:
                         st.error(f"Payment successful, but mailing failed: {tracking_ref}")
                         audit_engine.log_event(st.session_state.user_email, "FULFILL_FAIL", session_id, {"error": tracking_ref})
                else:
                    # Fallback if draft completely lost
                    st.warning("Payment received, but draft session was lost. Support has been notified.")
                    audit_engine.log_event(st.session_state.user_email, "GHOST_DRAFT_PAID", session_id, {})

            else:
                st.error("Payment Verification Failed or Cancelled.")
        
        # Clear URL to prevent re-triggering
        st.query_params.clear()

    # B. Handle View Routing (e.g. ?view=admin)
    view_param = query_params.get("view", None)
    if view_param == "legacy":
        st.session_state.app_mode = "legacy"
    elif view_param == "legal":
        st.session_state.app_mode = "legal"
    elif view_param == "admin":
        # Security check even for URL routing
        user_email = st.session_state.get("user_email", "")
        admin_emails = ["admin@verbapost.com", "tjkarat@gmail.com"]
        if st.session_state.get("authenticated") and user_email in admin_emails:
            st.session_state.app_mode = "admin"
        else:
            st.error("Access Denied. Please log in as an administrator.")
            st.session_state.app_mode = "login"

    # 4. Render Application based on App Mode
    mode = st.session_state.app_mode

    if mode == "splash":
        if ui_splash: ui_splash.render_splash_page()
        else: st.error("Splash module missing")

    elif mode == "login":
        if ui_login: ui_login.render_login_page()
        
    elif mode == "legacy":
        if ui_legacy: ui_legacy.render_legacy_page()
        
    elif mode == "legal":
        if ui_legal: ui_legal.render_legal_page()
        
    elif mode == "admin":
        user_email = st.session_state.get("user_email", "")
        admin_emails = ["admin@verbapost.com", "tjkarat@gmail.com"]
        if st.session_state.get("authenticated") and user_email in admin_emails:
             if ui_admin: ui_admin.render_admin_page()
        else:
             st.error("Access Denied.")
        
    # Default / Standard App Flow
    elif mode in ["store", "workspace", "review"]:
        if ui_main: ui_main.render_main()
    
    else:
        # Fallback
        if ui_main: ui_main.render_main()

if __name__ == "__main__":
    main()