import logging
import time
import json
from datetime import datetime

# --- INTERNAL ENGINE IMPORTS ---
# Ensure database connection is available for immediate persistence
import database

# --- LOGGING CONFIGURATION ---
# Setting up standard logger for local console backup
logger = logging.getLogger(__name__)

def log_event(user_email, event_type, description, details=None):
    """
    Records a high-integrity system event. 
    In bulk campaigns, this function acts as a synchronous lock to ensure 
    data is saved to the database before the system proceeds.
    """
    # 1. Prepare standardized metadata
    timestamp = datetime.utcnow().isoformat()
    details_json = details if details else {}
    
    # 2. Local fallback logging
    log_msg = f"AUDIT_EVENT | {user_email} | {event_type} | {description}"
    logger.info(log_msg)

    try:
        # 3. Construct the persistence payload for Supabase
        log_entry = {
            "user_email": user_email,
            "event_type": event_type,
            "description": description,
            "details": details_json,
            "created_at": timestamp,
            "platform": "VerbaPost_Web"
        }

        # 4. CRITICAL: Synchronous database commit
        # This prevents the 'silent success' issue by forcing a DB write 
        # before the mailing loop in ui_main.py moves to the next row.
        success = database.save_audit_log(log_entry)
        
        if not success:
            logger.error(f"Database rejection for audit event: {event_type}")
            # We return False but don't raise an exception to prevent app crash
            return False
            
        return True

    except Exception as e:
        # 5. Fail-safe error handling to ensure mailing doesn't stop if DB flickers
        err_msg = f"CRITICAL_AUDIT_FAILURE: {str(e)}"
        logger.error(err_msg)
        print(f"!!! {err_msg}")
        return False

def get_user_logs(user_email, limit=50):
    """
    Fetches the most recent logs for the Admin or User dashboard.
    """
    try:
        logs = database.get_audit_logs(user_email, limit=limit)
        return logs if logs else []
    except Exception as e:
        logger.error(f"Failed to fetch user logs: {e}")
        return []

def clear_old_logs(retention_days=90):
    """
    Maintenance function to prune old audit data.
    """
    # Placeholder for scheduled cleanup logic
    logger.info(f"Cleanup routine initialized for logs older than {retention_days} days.")
    return True

# --- CAMPAIGN SPECIFIC TRACKING ---

def log_campaign_milestone(user_email, campaign_id, milestone, success_count, fail_count):
    """
    Specific helper for the bulk_engine to track multi-step progress.
    """
    description = f"Milestone: {milestone} | S: {success_count} F: {fail_count}"
    return log_event(
        user_email=user_email,
        event_type="CAMPAIGN_PROGRESS",
        description=description,
        details={"campaign_id": campaign_id, "success": success_count, "fail": fail_count}
    )

# --- DEBUGGING UTILS ---

def verify_persistence():
    """Diagnostic check to ensure the engine can talk to database.py."""
    test_email = "system_check@verbapost.com"
    return log_event(test_email, "DIAGNOSTIC", "Checking database persistence.")

# End of Expanded Audit Engine