import logging
import datetime
import json
import streamlit as st

# --- IMPORTS ---
try:
    import database
except Exception:
    database = None

logger = logging.getLogger(__name__)

def log_event(user_email, event_type, session_id=None, metadata=None):
    """
    Logs critical system events to the database for security auditing.
    
    Args:
        user_email (str): The email of the user (or 'guest').
        event_type (str): Category (e.g., 'PAYMENT_CSRF_BLOCK', 'LOGIN_FAIL').
        session_id (str, optional): The Stripe or App session ID.
        metadata (dict, optional): Extra details like error messages or IP.
    """
    timestamp = datetime.datetime.utcnow().isoformat()
    
    # Ensure metadata is a string for storage
    meta_str = "{}"
    if metadata:
        try:
            meta_str = json.dumps(metadata)
        except Exception:
            meta_str = str(metadata)

    # 1. Console Log (Always happens)
    log_msg = f"[AUDIT] {timestamp} | {event_type} | User: {user_email} | {meta_str}"
    logger.info(log_msg)
    print(log_msg) # Force print to Cloud Run logs

    # 2. Database Log (If DB is connected)
    if database and hasattr(database, "supabase"):
        try:
            data = {
                "event_type": event_type,
                "user_email": user_email,
                "session_id": session_id,
                "metadata": metadata,  # Supabase handles JSONB automatically if configured
                "created_at": timestamp
            }
            # Attempt to insert into 'audit_events' table
            database.supabase.table("audit_events").insert(data).execute()
        except Exception as e:
            logger.error(f"Failed to write audit log to DB: {e}")