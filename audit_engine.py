import logging
import datetime
import json
import database  # Imports the SQLAlchemy setup

# --- CONFIGURATION ---
logger = logging.getLogger(__name__)

def log_event(user_email, event_type, session_id=None, metadata=None):
    """
    Logs critical system events to the database for security auditing.
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
    print(log_msg) # Force print for Cloud Run

    # 2. Database Log (SQLAlchemy)
    if database:
        try:
            with database.get_db_session() as db:
                # Use the AuditEvent model defined in database.py
                event = database.AuditEvent(
                    event_type=event_type,
                    user_email=user_email,
                    # Store session_id inside details if specific column is missing, 
                    # or update model if you have a session_id column.
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
    Defined specifically to match the call in ui_admin.py line 443.
    """
    if not database:
        return []
        
    try:
        with database.get_db_session() as db:
            # Query the AuditEvent table
            logs = db.query(database.AuditEvent).order_by(
                database.AuditEvent.timestamp.desc()
            ).limit(limit).all()
            
            # Convert to dicts for safe UI rendering
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
# This guarantees that if any older code calls 'get_recent_logs', it still works.
get_recent_logs = get_audit_logs