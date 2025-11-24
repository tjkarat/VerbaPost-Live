import streamlit as st
from supabase import create_client
from datetime import datetime

def get_client():
    try:
        url = st.secrets.get("SUPABASE_URL") or st.secrets["supabase"]["url"]
        key = st.secrets.get("SUPABASE_KEY") or st.secrets["supabase"]["key"]
        return create_client(url, key)
    except: return None

# --- USER PROFILE FUNCTIONS ---
def get_user_profile(email):
    """Fetch user address data"""
    sb = get_client()
    if not sb: return {}
    try:
        # Assuming table is 'user_profiles'
        res = sb.table("user_profiles").select("*").eq("email", email).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
    except: pass
    return {}

def update_user_profile(email, name, street, city, state, zip_code):
    """Save user address data"""
    sb = get_client()
    if not sb: return False
    try:
        data = {
            "full_name": name,
            "address_line1": street,
            "address_city": city,
            "address_state": state,
            "address_zip": zip_code,
            "email": email # Ensure email is present for upsert
        }
        # Upsert: Update if exists, Insert if new
        sb.table("user_profiles").upsert(data, on_conflict="email").execute()
        return True
    except Exception as e:
        print(f"Update Error: {e}")
        return False

# --- MAILROOM FUNCTIONS ---
def fetch_pending_letters():
    sb = get_client()
    if not sb: return []
    try:
        res = sb.table("letters").select("*").order("created_at", desc=True).execute()
        return res.data
    except: return []

def mark_as_sent(letter_id):
    sb = get_client()
    if sb: sb.table("letters").update({"status": "sent"}).eq("id", letter_id).execute()