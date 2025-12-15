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
    with st.sidebar:
        st.markdown("# 📮 VerbaPost")
        st.markdown("---")
        st.markdown("### 🧭 Navigation")
        if st.button("🏠 Home / Splash", use_container_width=True):
            st.session_state.app_mode = "splash"
            st.rerun()
        if st.button("🔐 Login / Account", use_container_width=True):
            st.session_state.app_mode = "login"
            st.rerun()
        
        user_email = st.session_state.get("user_email", "")
        admin_emails = ["admin@verbapost.com", "tjkarat@gmail.com"]
        if st.session_state.get("authenticated") and user_email in admin_emails:
            st.markdown("---")
            st.markdown("### 🛡️ Admin")
            if st.button("⚙️ Admin Console", use_container_width=True):
                st.session_state.app_mode = "admin"
                st.rerun()
        
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
    try:
        with database.get_db_session() as db:
            draft = db.query(database.LetterDraft).filter(database.LetterDraft.id == draft_id).first()
            if not draft: return False, "Draft Not Found"
            content = draft.transcription
            to_addr = json.loads(draft.recipient_json) if draft.recipient_json else {}
            from_addr = json.loads(draft.sender_json) if draft.sender_json else {}
            sig_text = draft.signature_data if hasattr(draft, 'signature_data') else None

        pdf_bytes = letter_format.create_pdf(content, to_addr, from_addr, tier="Legacy", font_choice="Caveat", signature_text=sig_text)
        
        api_key = secrets_manager.get_secret("postgrid.api_key")
        if not api_key: return False, "Missing API Key"
        
        files = {'pdf': ('letter.pdf', pdf_bytes, 'application/pdf')}
        data = {
            'to': json.dumps({'firstName': to_addr.get('name', '').split(' ')[0], 'lastName': ' '.join(to_addr.get('name', '').split(' ')[1:]), 'addressLine1': to_addr.get('street'), 'city': to_addr.get('city'), 'state': to_addr.get('state'), 'postalOrZip': to_addr.get('zip'), 'countryCode': 'US'}),
            'from': json.dumps({'firstName': from_addr.get('name', '').split(' ')[0], 'lastName': ' '.join(from_addr.get('name', '').split(' ')[1:]), 'addressLine1': from_addr.get('street'), 'city': from_addr.get('city'), 'state': from_addr.get('state'), 'postalOrZip': from_addr.get('zip'), 'countryCode': 'US'}),
            'certified': 'true',
            'description': f"Legacy Letter #{draft_id}"
        }
        res = requests.post("https://api.postgrid.com/print-mail/v1/letters", auth=(api_key, ''), data=data, files=files)
        
        if res.status_code in [200, 201]:
            tracking_ref = res.json().get('id')
            database.update_draft_data(draft_id, status="FULFILLED")
            email_engine.send_confirmation(user_email, tracking_number=tracking_ref, tier="Legacy Certified")
            return True, tracking_ref
        else:
            audit_engine.log_event(user_email, "POSTGRID_FAIL", str(draft_id), res.text)
            return False, f"Mailing Error: {res.text}"
    except Exception as e:
        audit_engine.log_event(user_email, "FULFILLMENT_EXCEPTION", str(draft_id), str(e))
        return False, str(e)

def main():
    if "authenticated" not in st.session_state: st.session_state.authenticated = False
    if "user_email" not in st.session_state: st.session_state.user_email = ""
    if "app_mode" not in st.session_state: st.session_state.app_mode = "splash"
    render_sidebar()
    
    query_params = st.query_params
    session_id = query_params.get("session_id", None)
    
    if session_id and session_id != st.session_state.get("last_processed_session"):
        with st.spinner("Verifying secure payment..."):
            result = payment_engine.verify_session(session_id)
            if result and result.get("paid"):
                st.session_state.last_processed_session = session_id
                payer_email = result.get("email")
                if payer_email: st.session_state.user_email = payer_email
                
                draft_id = st.session_state.get("current_legacy_draft_id")
                if not draft_id and payer_email:
                     with database.get_db_session() as db:
                         recent = db.query(database.LetterDraft).filter(database.LetterDraft.user_email == payer_email, database.LetterDraft.tier == 'Legacy', database.LetterDraft.status != 'FULFILLED').order_by(database.LetterDraft.created_at.desc()).first()
                         if recent:
                             draft_id = recent.id
                             st.session_state.current_legacy_draft_id = recent.id
                             st.session_state.legacy_text = recent.transcription

                if draft_id:
                    database.update_draft_data(draft_id, status="Paid", price=15.99)
                    success, tracking_ref = process_legacy_fulfillment(draft_id, st.session_state.user_email)
                    if success:
                        st.session_state.tracking_number = tracking_ref
                        st.session_state.paid_success = True
                        st.session_state.app_mode = "legacy"
                        # FIX 11: Show Amount
                        amount = result.get("amount_total", 0) / 100.0
                        st.balloons()
                        st.success(f"✅ Payment Confirmed: ${amount:.2f}")
                    else:
                         st.error(f"Payment successful, but mailing failed: {tracking_ref}")
                         audit_engine.log_event(st.session_state.user_email, "FULFILL_FAIL", session_id, {"error": tracking_ref})
                else:
                    st.warning("Payment received, but draft session was lost. Support has been notified.")
                    audit_engine.log_event(st.session_state.user_email, "GHOST_DRAFT_PAID", session_id, {})
            else: st.error("Payment Verification Failed or Cancelled.")
        st.query_params.clear()

    view_param = query_params.get("view", None)
    if view_param == "legacy": st.session_state.app_mode = "legacy"
    elif view_param == "legal": st.session_state.app_mode = "legal"
    elif view_param == "admin":
        user_email = st.session_state.get("user_email", "")
        admin_emails = ["admin@verbapost.com", "tjkarat@gmail.com"]
        if st.session_state.get("authenticated") and user_email in admin_emails: st.session_state.app_mode = "admin"
        else: st.error("Access Denied."); st.session_state.app_mode = "login"

    mode = st.session_state.app_mode
    if mode == "splash": ui_splash.render_splash_page() if ui_splash else st.error("Missing splash")
    elif mode == "login": ui_login.render_login_page() if ui_login else st.error("Missing login")
    elif mode == "legacy": ui_legacy.render_legacy_page() if ui_legacy else st.error("Missing legacy")
    elif mode == "legal": ui_legal.render_legal_page() if ui_legal else st.error("Missing legal")
    elif mode == "admin":
        if ui_admin: ui_admin.render_admin_page()
    elif mode in ["store", "workspace", "review"]: ui_main.render_main() if ui_main else st.error("Missing main")
    else: ui_main.render_main() if ui_main else st.error("Missing main fallback")

if __name__ == "__main__":
    main()