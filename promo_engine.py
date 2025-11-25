import streamlit as st
from supabase import create_client
from datetime import datetime

def get_client():
    try:
        url = st.secrets.get("SUPABASE_URL") or st.secrets["supabase"]["url"]
        key = st.secrets.get("SUPABASE_KEY") or st.secrets["supabase"]["key"]
        return create_client(url, key)
    except: return None

def create_code(new_code):
    """Admin: Creates a new promo code"""
    sb = get_client()
    if sb:
        try:
            sb.table("promo_codes").insert({"code": new_code.strip().upper()}).execute()
            return True, "Code Created"
        except Exception as e:
            return False, str(e)
    return False, "DB Error"

def get_all_codes_with_usage():
    """Admin: Returns list of codes and how many times used"""
    sb = get_client()
    if not sb: return []
    try:
        # Get codes
        codes = sb.table("promo_codes").select("*").execute().data
        # Get logs
        logs = sb.table("promo_logs").select("*").execute().data
        
        # Merge data
        data = []
        for c in codes:
            usage_count = len([x for x in logs if x['code'] == c['code']])
            data.append({
                "Code": c['code'],
                "Active": c['active'],
                "Times Used": usage_count,
                "Created": c['created_at']
            })
        return data
    except: return []

def validate_code(code_input):
    """User: Checks if code exists and is active"""
    sb = get_client()
    if not sb: return False
    try:
        res = sb.table("promo_codes").select("*").eq("code", code_input.strip().upper()).eq("active", True).execute()
        return len(res.data) > 0
    except: return False

def log_usage(code_input, user_email):
    """User: Logs that the code was used"""
    sb = get_client()
    if sb:
        try:
            sb.table("promo_logs").insert({
                "code": code_input.strip().upper(),
                "user_email": user_email,
                "used_at": datetime.now().isoformat()
            }).execute()
        except Exception as e:
            print(f"Logging Error: {e}")
