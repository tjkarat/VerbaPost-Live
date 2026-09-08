import requests
import json
import os
# Optional Streamlit: the FastAPI backend runs without it. The stub keeps the
# existing `hasattr(st, "secrets")` lookups safe (they fall through to env).
try:
    import streamlit as st
except ImportError:
    class _StreamlitStub:
        secrets = {}
        def __getattr__(self, _name):
            def _noop(*args, **kwargs):
                return None
            return _noop
    st = _StreamlitStub()
import logging

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
# We use the Print & Mail API for everything since that is likely the key you have.
POSTGRID_BASE_URL = "https://api.postgrid.com/print-mail/v1"

def get_api_key():
    """Retrieves PostGrid API Key from secrets."""
    if hasattr(st, "secrets") and "postgrid" in st.secrets:
        return st.secrets["postgrid"].get("api_key")
    return os.environ.get("POSTGRID_API_KEY")

def validate_address(address_dict):
    """
    Validates address by attempting to create a Contact in PostGrid.
    This works with the Print & Mail API key.
    """
    api_key = get_api_key()
    if not api_key: 
        logger.warning("PostGrid Key missing. Skipping validation (Soft Pass).")
        return True, "Dev Mode: Validation Skipped"

    # Use the Contacts endpoint. If the address is invalid, PostGrid returns a 400.
    url = f"{POSTGRID_BASE_URL}/contacts"

    payload = {
        "firstName": "Verification Check",
        "addressLine1": address_dict.get('street') or address_dict.get('address_line1'),
        "city": address_dict.get('city'),
        "provinceOrState": address_dict.get('state'),
        "postalOrZip": address_dict.get('zip_code') or address_dict.get('zip'),
        "countryCode": address_dict.get('country', "US")
    }

    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }

    try:
        # We try to create the contact. 
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code in [200, 201]:
            # Success! The address is valid and mailable.
            data = response.json()
            return True, data
            
        elif response.status_code == 400:
            # Address rejected
            error_msg = "Invalid Address"
            try:
                # Try to extract exact error from PostGrid response
                err_data = response.json()
                if 'error' in err_data:
                    error_msg = err_data['error'].get('message', str(err_data['error']))
            except:
                pass
            return False, f"PostGrid Rejected: {error_msg}"
            
        else:
            logger.error(f"PostGrid Error {response.status_code}: {response.text}")
            # If the API is down, we Soft Pass so we don't block signups
            return True, f"Service Warning ({response.status_code})"

    except Exception as e:
        logger.error(f"Validation Exception: {e}")
        return True, "Validation Offline (Soft Pass)"

def send_letter(pdf_bytes, to_addr, from_addr, description="VerbaPost Letter"):
    """
    Sends PDF via PostGrid Print & Mail API.
    """
    api_key = get_api_key()
    if not api_key: return None

    url = f"{POSTGRID_BASE_URL}/letters"

    files = {
        'pdf': ('letter.pdf', pdf_bytes, 'application/pdf')
    }

    # Helper to clean dictionary keys for PostGrid form-data
    form_data = {
        "to[firstName]": to_addr.get('name'),
        "to[addressLine1]": to_addr.get('street'),
        "to[city]": to_addr.get('city'),
        "to[provinceOrState]": to_addr.get('state'),
        "to[postalOrZip]": to_addr.get('zip'),
        "to[countryCode]": "US",
        
        "from[firstName]": from_addr.get('name'),
        "from[addressLine1]": from_addr.get('street'),
        "from[city]": from_addr.get('city'),
        "from[provinceOrState]": from_addr.get('state'),
        "from[postalOrZip]": from_addr.get('zip'),
        "from[countryCode]": "US",
        
        "description": description,
        "color": "true",
        "express": "false"
    }

    try:
        response = requests.post(
            url,
            headers={"x-api-key": api_key},
            files=files,
            data=form_data
        )

        if response.status_code in [200, 201]:
            return response.json().get('id')
        else:
            logger.error(f"PostGrid Send Failed: {response.text}")
            return None
    except Exception as e:
        logger.error(f"PostGrid Exception: {e}")
        return None

# ==========================================
# 🆕 INVITATION MAILING (prospect acquisition path)
# ==========================================

def is_test_mode():
    """PostGrid test keys start with test_; letters created with them are
    never printed. Surfaced in the advisor UI so nobody thinks a staging
    campaign went to real mailboxes."""
    key = get_api_key() or ""
    return key.startswith("test_")


def send_invitation_letter(pdf_bytes, to_addr, from_addr, description, idempotency_key):
    """
    Mail one invitation via PostGrid Print & Mail.
    to_addr/from_addr: {name, company, line1, line2, city, state, zip}
    Returns (postgrid_letter_id, None) or (None, error_string).

    Idempotency-Key makes a retried batch safe: PostGrid returns the
    original letter instead of printing a second copy.
    """
    api_key = get_api_key()
    if not api_key:
        return None, "POSTGRID_API_KEY missing"

    url = f"{POSTGRID_BASE_URL}/letters"
    first, _, last = (to_addr.get("name") or "").strip().partition(" ")
    ffirst, _, flast = (from_addr.get("name") or "").strip().partition(" ")
    form_data = {
        "to[firstName]": first or to_addr.get("name") or "Resident",
        "to[lastName]": last,
        "to[addressLine1]": to_addr.get("line1") or "",
        "to[addressLine2]": to_addr.get("line2") or "",
        "to[city]": to_addr.get("city") or "",
        "to[provinceOrState]": to_addr.get("state") or "",
        "to[postalOrZip]": to_addr.get("zip") or "",
        "to[countryCode]": "US",
        "from[firstName]": ffirst or from_addr.get("name") or "",
        "from[lastName]": flast,
        "from[companyName]": from_addr.get("company") or "",
        "from[addressLine1]": from_addr.get("line1") or "",
        "from[city]": from_addr.get("city") or "",
        "from[provinceOrState]": from_addr.get("state") or "",
        "from[postalOrZip]": from_addr.get("zip") or "",
        "from[countryCode]": "US",
        "description": description,
        "color": "false",
        "doubleSided": "false",
        "addressPlacement": "top_first_page",   # our PDF leaves the top 115mm clear
        "size": "us_letter",
    }
    form_data = {k: v for k, v in form_data.items() if v != ""}
    files = {"pdf": ("invitation.pdf", pdf_bytes, "application/pdf")}
    headers = {"x-api-key": api_key, "Idempotency-Key": str(idempotency_key)}
    try:
        response = requests.post(url, headers=headers, files=files, data=form_data, timeout=30)
        if response.status_code in (200, 201):
            return response.json().get("id"), None
        msg = response.text[:300]
        try:
            err = response.json().get("error", {})
            msg = err.get("message") or msg
        except Exception:
            pass
        logger.error(f"PostGrid invitation failed ({response.status_code}): {msg}")
        return None, f"{response.status_code}: {msg}"
    except Exception as e:
        logger.error(f"PostGrid invitation exception: {e}")
        return None, str(e)
