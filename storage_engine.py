import streamlit as st
from supabase import create_client
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

# Lazy Loader for Client
_supabase_storage_client = None

def get_storage_client():
    global _supabase_storage_client
    if _supabase_storage_client:
        return _supabase_storage_client
    try:
        # Re-using existing secrets
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        _supabase_storage_client = create_client(url, key)
        return _supabase_storage_client
    except Exception as e:
        logger.error(f"Storage Init Error: {e}")
        return None

def upload_audio(user_email, file_bytes, content_type="audio/mpeg"):
    """
    Uploads audio bytes to 'heirloom-audio' bucket.
    Returns: storage_path (e.g. 'user@email.com/20231225_uuid.mp3')
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
        # Create Signed URL valid for 1 hour
        response = client.storage.from_("heirloom-audio").create_signed_url(storage_path, expiry)
        
        # Handle Supabase Client response variations (Dict vs Str)
        if isinstance(response, dict) and 'signedURL' in response:
            return response['signedURL']
        elif isinstance(response, str):
            return response
        return response 
    except Exception as e:
        logger.error(f"Signed URL Error: {e}")
        return None