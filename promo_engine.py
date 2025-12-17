import logging
from datetime import datetime
from sqlalchemy import func
import database  # Uses your existing SQLAlchemy setup

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_code(code):
    """
    Checks if a promo code exists, is active, and has remaining uses.
    Returns (True, value) if valid, (False, reason) otherwise.
    """
    if not code: 
        return False, "Code is empty"
    
    code = code.strip().upper()
    
    if not database:
        return False, "Database Error"

    try:
        with database.get_db_session() as db:
            # 1. Check if code exists
            promo = db.query(database.PromoCode).filter(database.PromoCode.code == code).first()
            
            if not promo:
                return False, "Code not found"
            if not promo.active:
                return False, "Code is inactive"

            # 2. Check usage count (DEFENSIVE: Handle missing table)
            # This prevents the "AttributeError: module 'database' has no attribute 'PromoLog'" crash
            if hasattr(database, 'PromoLog'):
                usage_count = db.query(func.count(database.PromoLog.id)).filter(database.PromoLog.code == code).scalar()
                
                if usage_count >= promo.max_uses:
                    logger.warning(f"Promo code {code} exhausted ({usage_count}/{promo.max_uses})")
                    return False, "Limit Reached"
            else:
                # If table is missing, we log a warning but ALLOW the code (fail open) 
                # or block it. Here we allow it to prevent checkout blocking.
                logger.warning("PromoLog table missing in database. Skipping usage limit check.")

            # 3. Return success tuple
            discount_val = getattr(promo, 'value', 0.0)
            if discount_val == 0.0:
                discount_val = getattr(promo, 'discount_amount', 5.00) # Fallback
            
            return True, discount_val
            
    except Exception as e:
        logger.error(f"Error validating code {code}: {e}")
        return False, f"System Error: {str(e)}"

def log_usage(code, user_email):
    """
    Records usage by inserting a record into promo_logs.
    """
    if not code: return False
    code = code.strip().upper()
    
    # DEFENSIVE: Exit if table missing
    if not hasattr(database, 'PromoLog'):
        logger.warning("Cannot log promo usage: PromoLog model missing.")
        return False

    try:
        with database.get_db_session() as db:
            # Atomic check inside transaction
            promo = db.query(database.PromoCode).filter(database.PromoCode.code == code).first()
            if not promo: return False

            current_usage = db.query(func.count(database.PromoLog.id)).filter(database.PromoLog.code == code).scalar()
            
            if current_usage < promo.max_uses:
                log_entry = database.PromoLog(
                    code=code,
                    user_email=user_email,
                    used_at=datetime.utcnow()
                )
                db.add(log_entry)
                db.commit() # Commit explicitly
                return True
            return False
            
    except Exception as e:
        logger.error(f"Failed to log usage for {code}: {e}")
        return False

def create_code(code, max_uses=1, discount_amount=5.00):
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
            
            # Handle dynamic model attributes (value vs discount_amount)
            new_promo = database.PromoCode(
                code=code,
                max_uses=max_uses,
                active=True,
                created_at=datetime.utcnow()
            )
            
            # Set value if the column exists
            if hasattr(new_promo, 'value'):
                new_promo.value = discount_amount
            elif hasattr(new_promo, 'discount_amount'):
                new_promo.discount_amount = discount_amount
                
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
                usage_count = 0
                if hasattr(database, 'PromoLog'):
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