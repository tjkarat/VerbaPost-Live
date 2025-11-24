# promo_engine.py

# A simple list of single-use codes (replace with database lookup in production)
ACTIVE_PROMOS = {"LAUNCH2025": True, "FRIENDSOFVP": True}

def validate_code(code: str) -> bool:
    """Checks if a promo code is active and valid (case-insensitive)."""
    return code.upper() in ACTIVE_PROMOS and ACTIVE_PROMOS[code.upper()] is True

def redeem_code(code: str) -> bool:
    """Redeems the code by deactivating it in the system."""
    if validate_code(code):
        # In a real app, you would update the database here.
        # Here we simulate by just returning True for the flow
        # If using the global dict, you would set ACTIVE_PROMOS[code.upper()] = False
        return True
    return False

def generate_code() -> str:
    """Stub function for Admin Console."""
    return f"ADMIN-{uuid.uuid4().hex[:6].upper()}"

# Ensure UUID is imported for the generate_code stub
import uuid