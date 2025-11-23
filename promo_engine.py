import json
import os
import random
import string

PROMO_FILE = 'promo_codes.json'

def _load_promos():
    if not os.path.exists(PROMO_FILE):
        return {}
    with open(PROMO_FILE, 'r') as f:
        return json.load(f)

def _save_promos(codes):
    with open(PROMO_FILE, 'w') as f:
        json.dump(codes, f)

def generate_code():
    """Generates a random single-use code like 'VERBA-7X9A'"""
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    code = f"VERBA-{suffix}"
    codes = _load_promos()
    codes[code] = {"active": True, "type": "single_use"}
    _save_promos(codes)
    return code

def validate_code(code):
    """Checks if code exists and is active. Returns True/False."""
    codes = _load_promos()
    clean_code = code.strip().upper()
    if clean_code in codes and codes[clean_code]['active']:
        return True
    return False

def redeem_code(code):
    """Deactivates the code so it cannot be used again."""
    codes = _load_promos()
    clean_code = code.strip().upper()
    if clean_code in codes:
        codes[clean_code]['active'] = False
        _save_promos(codes)
        return True
    return False
