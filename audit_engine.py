import logging
import time
import json
from datetime import datetime

# --- INTERNAL ENGINE IMPORTS ---
import database

# --- LOGGING CONFIGURATION ---
logger = logging.getLogger(__name__)

def log_event(user_email, event_type, description, details=None):
    """
    Records a high-integrity system event. 
    """
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
        err_msg = f"CRITICAL_AUDIT_FAILURE: {str(e)}"
        logger.error(err_msg)
        return False

# FIXED: Restored function for Admin Console
def get_recent_logs(limit=100):
    try:
        # fetch logs for all users
        logs = database.get_audit_logs(None, limit=limit)
        return logs if logs else []
    except Exception as e:
        logger.error(f"Failed to fetch recent logs: {e}")
        return []

def get_user_logs(user_email, limit=50):
    try:
        logs = database.get_audit_logs(user_email, limit=limit)
        return logs if logs else []
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