import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import secrets_manager
import logging

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONNECTION ---
@st.cache_resource
def get_client():
    """
    Creates a Supabase client with robust secret fallback.
    """
    # 1. Try standard secrets manager
    url = secrets_manager.get_secret("supabase.url")
    key = secrets_manager.get_secret("supabase.key")

    # 2. Fallback: Check Streamlit secrets directly if manager fails
    if not url:
        try:
            url = st.secrets["supabase"]["url"]
            key = st.secrets["supabase"]["key"]
            logger.info("✅ Found Supabase keys in direct secrets (Fallback)")
        except:
            pass

    if not url or not key:
        logger.error("❌ Supabase URL or Key missing. Promo codes will not work.")
        return None

    try:
        return create_client(url, key)
    except Exception as e:
        logger.error(f"Supabase Connection Error: {e}")
        return None

# --- CORE FUNCTIONS ---
def create_code(new_code, max_uses=None):
    """
    Admin: Creates a new promo code.
    """
    sb = get_client()
    if sb:
        try:
            payload = {"code": new_code.strip().upper(), "active": True}
            if max_uses:
                payload["max_uses"] = int(max_uses)
                
            sb.table("promo_codes").insert(payload).execute()
            return True, "Code Created"
        except Exception as e:
            return False, str(e)
    return False, "Database Connection Failed"

def get_all_codes_with_usage():
    """Admin: Returns list of codes and usage stats"""
    sb = get_client()
    if not sb: return []
    try:
        # Fetch codes
        codes = sb.table("promo_codes").select("*").execute().data
        
        # Fetch logs to count usage
        # Note: In production, using .count() on the query is better than fetching all rows
        data = []
        for c in codes:
            # Count usage for this specific code
            usage_query = sb.table("promo_logs").select("id", count="exact").eq("code", c['code']).execute()
            usage_count = usage_query.count if usage_query.count is not None else 0
            
            limit = c.get('max_uses')
            limit_str = str(limit) if limit else "∞"
            
            data.append({
                "Code": c['code'],
                "Active": c['active'],
                "Used": usage_count,
                "Limit": limit_str,
                "Created": c.get('created_at', '')[:10]
            })
        return data
    except Exception as e:
        logger.error(f"Fetch Codes Error: {e}")
        return []

def validate_code(code_input):
    """User: Checks if code exists, is active, AND is under its usage limit"""
    sb = get_client()
    if not sb: return False
    
    code = code_input.strip().upper()
    
    try:
        # 1. Check if valid and active
        res = sb.table("promo_codes").select("*").eq("code", code).eq("active", True).execute()
        if not res.data or len(res.data) == 0:
            return False
        
        code_data = res.data[0]
        
        # 2. Check Usage Limit (if one exists)
        if code_data.get('max_uses'):
            usage_query = sb.table("promo_logs").select("id", count="exact").eq("code", code).execute()
            current_usage = usage_query.count
            
            if current_usage >= code_data['max_uses']:
                logger.warning(f"Code {code} hit limit ({current_usage}/{code_data['max_uses']})")
                return False

        return True
    except Exception as e:
        logger.error(f"Promo Validation Error: {e}")
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
            logger.error(f"Logging Error: {e}")