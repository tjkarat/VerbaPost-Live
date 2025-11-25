import streamlit as st
from supabase import create_client
from datetime import datetime

def get_client():
    try:
        url = st.secrets.get("SUPABASE_URL") or st.secrets["supabase"]["url"]
        key = st.secrets.get("SUPABASE_KEY") or st.secrets["supabase"]["key"]
        return create_client(url, key)
    except: return None

# --- USER PROFILES ---
def get_user_profile(email):
    sb = get_client()
    if not sb: return {}
    try:
        res = sb.table("user_profiles").select("*").eq("email", email).execute()
        if res.data: return res.data[0]
    except: pass
    return {}

def update_user_profile(email, name, street, city, state, zip_code):
    sb = get_client()
    if not sb: return False
    try:
        data = {
            "email": email, "full_name": name,
            "address_line1": street, "address_city": city,
            "address_state": state, "address_zip": zip_code
        }
        sb.table("user_profiles").upsert(data, on_conflict="email").execute()
        return True
    except: return False

# --- LETTERS ---
def fetch_pending_letters():
    sb = get_client()
    if not sb: return []
    try:
        return sb.table("letters").select("*").order("created_at", desc=True).execute().data
    except: return []

def mark_as_sent(letter_id):
    sb = get_client()
    if sb: sb.table("letters").update({"status": "sent"}).eq("id", letter_id).execute()

# --- UPDATED SAVE FUNCTION (FIXES TYPE ERROR) ---
def save_draft(user_email, text, tier, price, recipient_data=None, status="pending"):
    """
    Saves letter. Accepts custom status (e.g., 'sent_api').
    """
    sb = get_client()
    if sb:
        data = {
            "user_email": user_email,
            "body_text": text,
            "tier": tier,
            "price": price,
            "status": status,  # Now uses the passed status
            "created_at": datetime.now().isoformat()
        }
        
        if recipient_data:
            data.update({
                "recipient_name": recipient_data.get("name"),
                "recipient_street": recipient_data.get("street"),
                "recipient_city": recipient_data.get("city"),
                "recipient_state": recipient_data.get("state"),
                "recipient_zip": recipient_data.get("zip")
            })
            
        sb.table("letters").insert(data).execute()