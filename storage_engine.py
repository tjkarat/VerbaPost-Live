import streamlit as st
from supabase import create_client
import logging
import uuid
from datetime import datetime
import os

# --- IMPORT SECRETS MANAGER ---
try: import secrets_manager
except ImportError: secrets_manager = None

logger = logging.getLogger(__name__)

# Lazy Loader for Client
_supabase_storage_client = None

def get_storage_client():
    global _supabase_storage_client
    if _supabase_storage_client:
        return _supabase_storage_client
    
    url = None
    key = None

    # 1. Try Secrets Manager (Production/GCP)
    if secrets_manager:
        url = secrets_manager.get_secret("SUPABASE_URL") or secrets_manager.get_secret("supabase.url")
        key = secrets_manager.get_secret("SUPABASE_KEY") or secrets_manager.get_secret("supabase.key")

    # 2. Fallback: Streamlit Secrets (Local/QA)
    if not url and hasattr(st, "secrets") and "supabase" in st.secrets:
        try:
            url = st.secrets["supabase"]["url"]
            key = st.secrets["supabase"]["key"]
        except KeyError: pass

    # 3. Last Resort: Raw Env Vars
    if not url:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        logger.error("Storage Error: Missing SUPABASE_URL or SUPABASE_KEY")
        return None

    try:
        _supabase_storage_client = create_client(url, key)
        return _supabase_storage_client
    except Exception as e:
        logger.error(f"Storage Init Error: {e}")
        return None

def upload_audio(user_email, file_bytes, content_type="audio/mpeg"):
    """
    Uploads audio bytes to 'heirloom-audio' bucket.
    """
    client = get_storage_client()
    if not client: return None

    try:
        # Create secure, unique path
        filename = f"{datetime.now().strftime('%Y%m%d')}_{str(uuid.uuid4())[:8]}.mp3"
        storage_path = f"{user_email}/{filename}"
        
        # Upload
        client.storage.from_("heirloom-audio").upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": content_type}
        )
        return storage_path
    except Exception as e:
        logger.error(f"Upload Failed: {e}")
        return None

def get_signed_url(storage_path, expiry=3600):
    """
    Generates a secure, temporary link for playback.
    """
    if not storage_path: return None
    client = get_storage_client()
    if not client: return None
    
    try:
        response = client.storage.from_("heirloom-audio").create_signed_url(storage_path, expiry)
        
        if isinstance(response, dict) and 'signedURL' in response:
            return response['signedURL']
        elif isinstance(response, str):
            return response
        return response 
    except Exception as e:
        logger.error(f"Signed URL Error: {e}")
        return None