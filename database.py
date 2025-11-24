import streamlit as st
from supabase import create_client
from datetime import datetime

# --- CONNECT TO DB ---
def get_client():
    try:
        url = st.secrets.get("SUPABASE_URL") or st.secrets["supabase"]["url"]
        key = st.secrets.get("SUPABASE_KEY") or st.secrets["supabase"]["key"]
        return create_client(url, key)
    except:
        return None

# --- MAILROOM FUNCTIONS ---
def fetch_pending_letters():
    """Gets all letters that need to be printed"""
    sb = get_client()
    if not sb: return []
    
    try:
        # Fetching all records from 'letters' table
        # If you haven't created this table yet, Supabase will return an error,
        # but we handle it gracefully in the UI.
        res = sb.table("letters").select("*").order("created_at", desc=True).execute()
        return res.data
    except Exception as e:
        print(f"DB Error: {e}")
        return []

def mark_as_sent(letter_id):
    """Updates status to 'sent'"""
    sb = get_client()
    if sb:
        sb.table("letters").update({"status": "sent", "sent_at": datetime.now().isoformat()}).eq("id", letter_id).execute()

# --- USER FUNCTIONS ---
def save_draft(user_email, text, tier, price):
    """Saves a draft letter"""
    sb = get_client()
    if sb:
        data = {
            "user_email": user_email,
            "body_text": text,
            "tier": tier,
            "price": price,
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }
        sb.table("letters").insert(data).execute()