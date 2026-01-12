import logging
import streamlit as st

logger = logging.getLogger(__name__)

def run_preflight_checks():
    """
    Verifies that critical system components are reachable 
    before the UI renders.
    """
    results = {"status": True, "errors": []}
    
    # 1. Check Secrets
    try:
        import secrets_manager
        if not secrets_manager.get_secret("supabase.url"):
            results["errors"].append("Supabase URL missing in secrets.")
            results["status"] = False
    except Exception as e:
        results["errors"].append(f"Secrets Manager Error: {e}")
        results["status"] = False

    # 2. Check Database Connection
    try:
        import database
        with database.get_db_session() as session:
            from sqlalchemy import text
            session.execute(text("SELECT 1"))
    except Exception as e:
        results["errors"].append(f"Database Connection Failed: {e}")
        results["status"] = False

    if not results["status"]:
        for err in results["errors"]:
            logger.error(f"PREFLIGHT ERROR: {err}")
            
    return results