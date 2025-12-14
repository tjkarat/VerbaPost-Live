import streamlit as st
import datetime
import logging
from supabase import create_client
import secrets_manager

logger = logging.getLogger(__name__)

def log_event(user_email, event_type, session_id, metadata=None):
    """
    Logs critical system events to Supabase 'audit_events' table.
    Fails silently to prevent blocking the user experience.
    """
    try:
        # 1. Console Log (Always safe)
        timestamp = datetime.datetime.now().isoformat()
        log_entry = f"[AUDIT] {timestamp} | {user_email} | {event_type} | {session_id}"
        print(log_entry)
        
        # 2. Database Log
        url = secrets_manager.get_secret("supabase.url")
        key = secrets_manager.get_secret("supabase.key")
        
        if url and key:
            client = create_client(url, key)
            payload = {
                "user_email": user_email,
                "event_type": event_type,
                "session_id": session_id,
                "metadata": metadata or {},
                "created_at": timestamp
            }
            client.table("audit_events").insert(payload).execute()
            
    except Exception as e:
        # Never crash the app because of a log failure
        logger.error(f"Audit Log Failed: {e}")