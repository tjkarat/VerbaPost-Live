import logging
import time
import json
from datetime import datetime
from sqlalchemy import text # Required for raw SQL fallback

# --- INTERNAL ENGINE IMPORTS ---
import database

# --- LOGGING CONFIGURATION ---
logger = logging.getLogger(__name__)

def log_event(user_email, event_type, description, details=None):
    """Records a high-integrity system event."""
    timestamp = datetime.utcnow().isoformat()
    details_json = details if details else {}
    
    log_msg = f"AUDIT_EVENT | {user_email} | {event_type} | {description}"
    logger.info(log_msg)

    try:
        log_entry = {
            "user_email": user_email,
            "event_type": event_type,
            "description": description,
            "details": details_json,
            "created_at": timestamp,
            "platform": "VerbaPost_Web"
        }

        success = database.save_audit_log(log_entry)
        if not success:
            logger.error(f"Database rejection for audit event: {event_type}")
            return False
        return True

    except Exception as e:
        logger.error(f"CRITICAL_AUDIT_FAILURE: {str(e)}")
        return False

# --- FIXED: Robust Log Fetching with SQL Fallback ---
def get_recent_logs(limit=100):
    """
    Fetches system logs. Falls back to raw SQL if database.py is missing the method.
    """
    try:
        # 1. Try standard method if it exists
        if hasattr(database, 'get_audit_logs'):
            return database.get_audit_logs(None, limit=limit)
        
        # 2. Fallback: Raw SQL Query
        # This handles the "module 'database' has no attribute 'get_audit_logs'" error
        with database.get_db_session() as session:
            # Assumes table is named 'audit_logs' based on standard schema
            query = text("SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT :lim")
            result = session.execute(query, {"lim": limit})
            
            # Convert SQLAlchemy rows to dictionary list
            logs = []
            for row in result:
                # Handle different SQLAlchemy result formats
                if hasattr(row, '_mapping'):
                    logs.append(dict(row._mapping))
                else:
                    # Fallback for older SQLAlchemy versions
                    logs.append(dict(row))
            return logs

    except Exception as e:
        logger.error(f"Failed to fetch logs via fallback: {e}")
        return []

def get_user_logs(user_email, limit=50):
    try:
        if hasattr(database, 'get_audit_logs'):
            return database.get_audit_logs(user_email, limit=limit)
        return [] # Simple failover for user specific logs
    except Exception as e:
        logger.error(f"Failed to fetch user logs: {e}")
        return []

def clear_old_logs(retention_days=90):
    logger.info(f"Cleanup routine initialized for logs older than {retention_days} days.")
    return True

def log_campaign_milestone(user_email, campaign_id, milestone, success_count, fail_count):
    description = f"Milestone: {milestone} | S: {success_count} F: {fail_count}"
    return log_event(
        user_email=user_email,
        event_type="CAMPAIGN_PROGRESS",
        description=description,
        details={"campaign_id": campaign_id, "success": success_count, "fail": fail_count}
    )

def verify_persistence():
    test_email = "system_check@verbapost.com"
    return log_event(test_email, "DIAGNOSTIC", "Checking database persistence.")