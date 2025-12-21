import logging
import datetime
import json
import database  # Imports the SQLAlchemy setup

# --- CONFIGURATION ---
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
    timestamp = datetime.datetime.utcnow()
    
    # 1. Console Log (Always happens for cloud observability)
    meta_str = "{}"
    if metadata:
        try:
            meta_str = json.dumps(metadata)
        except Exception:
            meta_str = str(metadata)
            
    log_msg = f"[AUDIT] {event_type} | User: {user_email} | {meta_str}"
    logger.info(log_msg)
    # Force print to standard output for Cloud Run logs
    print(log_msg) 

    # 2. Database Log (SQLAlchemy)
    if database:
        try:
            with database.get_db_session() as db:
                # Use the AuditEvent model defined in database.py
                event = database.AuditEvent(
                    event_type=event_type,
                    user_email=user_email,
                    # We store session_id inside details/metadata or separate column if schema allows.
                    details=meta_str,
                    timestamp=timestamp
                )
                db.add(event)
                # Context manager auto-commits here
        except Exception as e:
            logger.error(f"Failed to write audit log to DB: {e}")

def get_audit_logs(limit=50):
    """
    Retrieves the most recent audit logs for the Admin Console.
    Renamed from get_recent_logs to match ui_admin.py call.
    """
    if not database:
        return []
        
    try:
        with database.get_db_session() as db:
            logs = db.query(database.AuditEvent).order_by(
                database.AuditEvent.timestamp.desc()
            ).limit(limit).all()
            
            # Convert to dicts for safe consumption
            results = []
            for log in logs:
                results.append({
                    "id": log.id,
                    "time": log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "type": log.event_type,
                    "user": log.user_email,
                    "details": log.details
                })
            return results
    except Exception as e:
        logger.error(f"Failed to fetch audit logs: {e}")
        return []

# --- SAFETY ALIAS ---
# This ensures that if any other file calls the old name, it still works.
get_recent_logs = get_audit_logs