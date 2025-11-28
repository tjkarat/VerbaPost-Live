import streamlit as st
from supabase import create_client
from datetime import datetime
import secrets_manager

def get_client():
    try:
        url = secrets_manager.get_secret("supabase.url")
        key = secrets_manager.get_secret("supabase.key")
        return create_client(url, key)
    except: return None

def create_code(new_code, max_uses=None):
    """
    Admin: Creates a new promo code.
    Optional: max_uses (int) to limit how many times it can be redeemed.
    """
    sb = get_client()
    if sb:
        try:
            payload = {"code": new_code.strip().upper()}
            if max_uses:
                payload["max_uses"] = int(max_uses)
                
            sb.table("promo_codes").insert(payload).execute()
            return True, "Code Created"
        except Exception as e:
            return False, str(e)
    return False, "DB Error"

def get_all_codes_with_usage():
    """Admin: Returns list of codes and usage stats"""
    sb = get_client()
    if not sb: return []
    try:
        codes = sb.table("promo_codes").select("*").execute().data
        logs = sb.table("promo_logs").select("*").execute().data
        
        data = []
        for c in codes:
            usage_count = len([x for x in logs if x['code'] == c['code']])
            limit = c.get('max_uses', '∞')
            
            data.append({
                "Code": c['code'],
                "Active": c['active'],
                "Used": usage_count,
                "Limit": limit,
                "Created": c['created_at']
            })
        return data
    except: return []

def validate_code(code_input):
    """User: Checks if code exists, is active, AND is under its usage limit"""
    sb = get_client()
    if not sb: return False
    
    code = code_input.strip().upper()
    
    try:
        # 1. Check if valid and active
        res = sb.table("promo_codes").select("*").eq("code", code).eq("active", True).execute()
        if len(res.data) == 0: return False
        
        code_data = res.data[0]
        
        # 2. Check Usage Limit (if one exists)
        if code_data.get('max_uses'):
            # Count current logs
            logs = sb.table("promo_logs").select("id", count="exact").eq("code", code).execute()
            current_usage = logs.count
            
            if current_usage >= code_data['max_uses']:
                print(f"Code {code} hit limit ({current_usage}/{code_data['max_uses']})")
                return False

        return True
    except Exception as e:
        print(f"Promo Validation Error: {e}")
        return False

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