import logging
from datetime import datetime
from sqlalchemy import func
import database  # Uses your existing SQLAlchemy setup

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_code(code):
    """
    Checks if a promo code exists and has remaining uses.
    Returns True if valid, False otherwise.
    """
    if not code: 
        return False
    
    # Normalize
    code = code.strip().upper()
    
    if not database:
        logger.error("Database module missing.")
        return False

    try:
        with database.get_db_session() as db:
            # 1. Check if code exists and is active
            promo = db.query(database.PromoCode).filter(database.PromoCode.code == code).first()
            
            if not promo:
                return False

            # Check active status
            if not promo.active:
                return False

            # 2. Check usage count via logs
            usage_count = db.query(func.count(database.PromoLog.id)).filter(database.PromoLog.code == code).scalar()
            
            if usage_count < promo.max_uses:
                return True
            else:
                logger.warning(f"Promo code {code} exhausted ({usage_count}/{promo.max_uses})")
                return False
            
    except Exception as e:
        logger.error(f"Error validating code {code}: {e}")
        return False

def log_usage(code, user_email):
    """
    Records usage by inserting a record into promo_logs.
    """
    if not code: return
    
    code = code.strip().upper()
    
    try:
        with database.get_db_session() as db:
            # Create a log entry
            log_entry = database.PromoLog(
                code=code,
                user_email=user_email,
                used_at=datetime.utcnow()
            )
            db.add(log_entry)
            logger.info(f"💰 Promo {code} used by {user_email}.")
            
    except Exception as e:
        logger.error(f"Failed to log usage for {code}: {e}")

def create_code(code, max_uses=1):
    """
    Admin function to generate new promo codes.
    """
    if not code: return False, "Code cannot be empty"
    
    code = code.strip().upper()
    
    try:
        with database.get_db_session() as db:
            # Check if code already exists
            existing = db.query(database.PromoCode).filter(database.PromoCode.code == code).first()
            if existing:
                return False, f"Code '{code}' already exists."
            
            new_promo = database.PromoCode(
                code=code,
                max_uses=max_uses,
                active=True,
                created_at=datetime.utcnow()
            )
            db.add(new_promo)
            
        return True, f"✅ Created code: {code} (Limit: {max_uses})"
        
    except Exception as e:
        logger.error(f"Create Promo Error: {e}")
        return False, f"Database Error: {str(e)}"

def get_all_codes_with_usage():
    """
    Returns a list of dictionaries for the Admin Dashboard.
    """
    try:
        with database.get_db_session() as db:
            promos = db.query(database.PromoCode).order_by(database.PromoCode.created_at.desc()).all()
            
            results = []
            for p in promos:
                # Calculate current usage on the fly
                usage_count = db.query(func.count(database.PromoLog.id)).filter(database.PromoLog.code == p.code).scalar()
                
                results.append({
                    "Code": p.code,
                    "Used": usage_count,
                    "Max Limit": p.max_uses,
                    "Remaining": p.max_uses - usage_count,
                    "Active": p.active,
                    "Created At": p.created_at.strftime("%Y-%m-%d")
                })
            return results
            
    except Exception as e:
        logger.error(f"Fetch Promos Error: {e}")
        return []