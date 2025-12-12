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
            # Query the PromoCode table defined in database.py
            promo = db.query(database.PromoCode).filter(database.PromoCode.code == code).first()
            
            if promo:
                # Check if usage limit is reached
                # The schema uses 'current_uses' vs 'max_uses'
                if promo.current_uses < promo.max_uses:
                    return True
                else:
                    logger.warning(f"Promo code {code} exhausted ({promo.current_uses}/{promo.max_uses})")
            return False
            
    except Exception as e:
        logger.error(f"Error validating code {code}: {e}")
        return False

def log_usage(code, user_email):
    """
    Increments the usage count for a specific code.
    """
    if not code: return
    
    code = code.strip().upper()
    
    try:
        with database.get_db_session() as db:
            promo = db.query(database.PromoCode).filter(database.PromoCode.code == code).first()
            if promo:
                promo.current_uses += 1
                # The session manager in database.py auto-commits on exit
                logger.info(f"💰 Promo {code} used by {user_email}. Count: {promo.current_uses}")
            else:
                logger.warning(f"Attempted to log usage for non-existent code: {code}")
                
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
                current_uses=0,
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
            
            return [
                {
                    "Code": p.code,
                    "Used": p.current_uses,
                    "Max Limit": p.max_uses,
                    "Remaining": p.max_uses - p.current_uses,
                    "Created At": p.created_at.strftime("%Y-%m-%d")
                }
                for p in promos
            ]
    except Exception as e:
        logger.error(f"Fetch Promos Error: {e}")
        return []