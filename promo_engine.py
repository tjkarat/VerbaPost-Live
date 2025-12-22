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
            if hasattr(database, 'PromoLog'):
                try:
                    usage_count = db.query(func.count(database.PromoLog.id)).filter(database.PromoLog.code == code).scalar() or 0
                    
                    if promo.max_uses and usage_count >= promo.max_uses:
                        logger.warning(f"Promo code {code} exhausted ({usage_count}/{promo.max_uses})")
                        return False, "Limit Reached"
                except Exception:
                    logger.warning("Error checking usage count. Allowing.")
            else:
                logger.warning("PromoLog table missing in database. Skipping usage limit check.")

            # 3. Return success tuple
            # FIX: Eagerly look for ANY non-zero value from DB
            val_a = getattr(promo, 'value', 0.0)
            val_b = getattr(promo, 'discount_amount', 0.0)
            
            final_val = val_a if val_a > 0 else val_b
            
            # --- LOGIC UPDATE: ZERO OUT COST ---
            # If the DB value is 0.0 (default) or low, we override it to 50.00.
            # This ensures it covers the cost of any letter ($15.99) or sub ($19.00),
            # effectively making the total $0.00.
            if final_val <= 0:
                 final_val = 50.00
            
            return True, float(final_val)
            
    except Exception as e:
        logger.error(f"Error validating code {code}: {e}")
        return False, f"System Error: {str(e)}"

def log_usage(code, user_email):
    """
    Records usage by inserting a record into promo_logs.
    """
    if not code: return False
    code = code.strip().upper()
    
    if not hasattr(database, 'PromoLog'):
        logger.warning("Cannot log promo usage: PromoLog model missing.")
        return False

    try:
        with database.get_db_session() as db:
            promo = db.query(database.PromoCode).filter(database.PromoCode.code == code).first()
            if not promo: return False

            current_usage = db.query(func.count(database.PromoLog.id)).filter(database.PromoLog.code == code).scalar() or 0
            
            # Only log if we haven't hit the limit (or if no limit exists)
            if promo.max_uses is None or current_usage < promo.max_uses:
                log_entry = database.PromoLog(
                    code=code,
                    user_email=user_email,
                    used_at=datetime.utcnow()
                )
                db.add(log_entry)
                db.commit() 
                return True
            return False
            
    except Exception as e:
        logger.error(f"Failed to log usage for {code}: {e}")
        return False

def create_code(code, max_uses=1, discount_amount=50.00):
    """
    Admin function to generate new promo codes.
    Default discount set to 50.00 to ensure 100% off for standard items.
    """
    if not code: return False, "Code cannot be empty"
    
    code = code.strip().upper()
    
    try:
        with database.get_db_session() as db:
            existing = db.query(database.PromoCode).filter(database.PromoCode.code == code).first()
            if existing:
                return False, f"Code '{code}' already exists."
            
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
            db.commit() # Ensure commit happens
            
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
                     usage_count = db.query(func.count(database.PromoLog.id)).filter(database.PromoLog.code == p.code).scalar() or 0
                
                # Safe attribute access
                limit = getattr(p, 'max_uses', 0) or 0
                remaining = (limit - usage_count) if limit else "∞"
                
                results.append({
                    "Code": p.code,
                    "Used": usage_count,
                    "Max Limit": limit,
                    "Remaining": remaining,
                    "Active": p.active,
                    "Created At": p.created_at.strftime("%Y-%m-%d") if p.created_at else "?"
                })
            return results
            
    except Exception as e:
        logger.error(f"Fetch Promos Error: {e}")
        return []