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
#
# Two providers. PCM (PostcardMania) is the live one; PostGrid remains as a
# fallback because the rest of this file already speaks it. Which one runs is
# decided by MAIL_PROVIDER, defaulting to PCM when PCM credentials exist.
#
#   MAIL_PROVIDER   = pcm | postgrid
#   PCM_BASE_URL    = https://v3.pcmintegrations.com  (PCM ships one server;
#                     Sandbox vs Production is a property of which apiKey/
#                     apiSecret pair you use, not a different host)
#   PCM_API_KEY     = apiKey  from PCM's Portal -> My Account -> API Keys
#   PCM_API_SECRET  = apiSecret, same page
#   PCM_ENVIRONMENT = sandbox | production (default production) — informational
#                     only, since PCM's API gives no way to ask which
#                     environment a key belongs to; set this by hand to match
#                     whichever key pair is in PCM_API_KEY/PCM_API_SECRET so
#                     the portal can say "test mode" truthfully.
#
# ---------------------------------------------------------------------------
# Confirmed against PCM's own OpenAPI 3.0 spec (DirectMail API v3):
#
#   1. POST {PCM_BASE_URL}/auth/login  {"apiKey", "apiSecret"}
#        -> 200 {"token": "<JWT>", "expires": "<ISO 8601>"}
#      Every other call authenticates with that JWT as a Bearer token, not
#      with the API key/secret directly. We cache the token and re-login
#      once it is within 60s of expiring.
#
#   2. POST {PCM_BASE_URL}/order/letter   Authorization: Bearer <token>
#        -> 201 {"batchID": int, "orderID": int, "extRefNbr": str}
#        -> 409 if extRefNbr was already used for a previous order
#        -> 422 if the recipient address fails PCM's own verification
#
#   The `letter` field is the artwork for the WHOLE order and only accepts
#   raw HTML or a URL PCM will fetch (there is no base64/binary upload path,
#   and there is no per-recipient artwork field) — so a personalized piece
#   per prospect means one PCM order per recipient, each pointing at that
#   person's own hosted PDF. We host it at
#   `{BASE_URL}/a/{slug}/i/{token}/pdf` (see app/prospect.py) and PCM fetches
#   it while processing the order.
#
#   `insertAddressingPage: true` + `envelope.type: "fullWindow"` tells PCM to
#   generate and insert its own address page rather than requiring the
#   address to be pre-printed into the artwork, so invitation_format.py's
#   blank top zone (built for PostGrid's overlay) is simply unused space here
#   — harmless, not wrong.
# ---------------------------------------------------------------------------

PCM_DEFAULT_BASE = "https://v3.pcmintegrations.com"

_pcm_token_cache = {"token": None, "expires": None}


def get_mail_provider():
    explicit = (os.environ.get("MAIL_PROVIDER") or "").strip().lower()
    if explicit in ("pcm", "postgrid"):
        return explicit
    return "pcm" if get_pcm_api_key() else "postgrid"


def get_pcm_api_key():
    for name in ("PCM_API_KEY", "pcm.api_key"):
        val = os.environ.get(name)
        if val:
            return val.strip()
    return None


def get_pcm_api_secret():
    for name in ("PCM_API_SECRET", "pcm.api_secret"):
        val = os.environ.get(name)
        if val:
            return val.strip()
    return None


def get_pcm_base_url():
    return (os.environ.get("PCM_BASE_URL") or PCM_DEFAULT_BASE).rstrip("/")


def is_test_mode():
    """True when mail is going somewhere that does not physically print.
    PCM: no API signal exists for this (Sandbox vs Production is which
    apiKey/apiSecret you used), so it follows the explicit PCM_ENVIRONMENT
    env var. PostGrid: a key beginning test_. Surfaced in the advisor portal
    so a staging run is never mistaken for real mail."""
    if get_mail_provider() == "pcm":
        return (os.environ.get("PCM_ENVIRONMENT") or "").strip().lower() == "sandbox"
    return (get_api_key() or "").startswith("test_")


def _pcm_login(force=False):
    """POST /auth/login, cache the JWT until ~60s before it expires.
    Returns (token, None) or (None, error)."""
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    if not force and _pcm_token_cache["token"] and _pcm_token_cache["expires"]:
        if _pcm_token_cache["expires"] - timedelta(seconds=60) > now:
            return _pcm_token_cache["token"], None

    key, secret = get_pcm_api_key(), get_pcm_api_secret()
    if not key or not secret:
        return None, "PCM_API_KEY / PCM_API_SECRET missing"
    url = f"{get_pcm_base_url()}/auth/login"
    try:
        response = requests.post(url, json={"apiKey": key, "apiSecret": secret},
                                 headers={"Content-Type": "application/json",
                                          "Accept": "application/json"}, timeout=30)
        if response.status_code != 200:
            msg = response.text[:400]
            logger.error(f"PCM login failed ({response.status_code}): {msg}")
            return None, f"login {response.status_code}: {msg}"
        data = response.json()
        token = data.get("token")
        if not token:
            return None, f"PCM login returned no token: {str(data)[:200]}"
        expires_raw = data.get("expires")
        try:
            expires = datetime.fromisoformat(expires_raw.replace("Z", "+00:00")) if expires_raw else now + timedelta(minutes=10)
        except Exception:
            expires = now + timedelta(minutes=10)
        _pcm_token_cache["token"] = token
        _pcm_token_cache["expires"] = expires
        return token, None
    except Exception as e:
        logger.error(f"PCM login exception: {e}")
        return None, str(e)


def _pcm_auth_headers():
    token, err = _pcm_login()
    if not token:
        return None, err
    return {"Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"}, None


def _pcm_letter_payload(pdf_url, to_addr, from_addr, idempotency_key):
    """Build the PCM /order/letter body per the confirmed LetterOrderRequest
    schema (PCM's DirectMail API v3 OpenAPI spec)."""
    first, _, last = (to_addr.get("name") or "").strip().partition(" ")
    recipient = {
        "firstName": first or to_addr.get("name") or "Resident",
        "lastName": last,
        "address": to_addr.get("line1") or "",
        "city": to_addr.get("city") or "",
        "state": to_addr.get("state") or "",
        "zipCode": to_addr.get("zip") or "",
        "extRefNbr": str(idempotency_key),
    }
    if to_addr.get("line2"):
        recipient["address2"] = to_addr["line2"]

    return_address = {
        "firstName": from_addr.get("name") or "",
        "company": from_addr.get("company") or "",
        "address": from_addr.get("line1") or "",
        "city": from_addr.get("city") or "",
        "state": from_addr.get("state") or "",
        "zipCode": from_addr.get("zip") or "",
    }
    return_address = {k: v for k, v in return_address.items() if v}

    return {
        "mailClass": "FirstClass",
        "recipients": [recipient],
        "letterStock": "Regular",
        "color": True,
        "printOnBothSides": False,
        "insertAddressingPage": True,
        "envelope": {"type": "fullWindow"},
        "letter": pdf_url,
        "returnAddress": return_address,
        "extRefNbr": str(idempotency_key),
    }


def _send_via_pcm(pdf_url, to_addr, from_addr, idempotency_key):
    if not pdf_url:
        return None, "no public PDF URL to give PCM (BASE_URL not reachable?)"
    headers, err = _pcm_auth_headers()
    if not headers:
        return None, f"PCM auth failed: {err}"
    url = f"{get_pcm_base_url()}/order/letter"
    payload = _pcm_letter_payload(pdf_url, to_addr, from_addr, idempotency_key)
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=45)
        if response.status_code == 401:
            # Token may have been revoked/expired early; one forced re-login+retry.
            token, login_err = _pcm_login(force=True)
            if token:
                headers = {"Authorization": f"Bearer {token}",
                           "Content-Type": "application/json", "Accept": "application/json"}
                response = requests.post(url, json=payload, headers=headers, timeout=45)
        if response.status_code == 201:
            data = response.json()
            pcm_id = data.get("orderID") or data.get("batchID")
            if not pcm_id:
                return None, f"PCM accepted but returned no id: {str(data)[:200]}"
            return str(pcm_id), None
        if response.status_code == 409:
            return None, "PCM: extRefNbr already used for a prior order (duplicate send)"
        if response.status_code == 422:
            return None, f"PCM: address failed verification: {response.text[:300]}"
        msg = response.text[:400]
        logger.error(f"PCM letter order failed ({response.status_code}): {msg}")
        return None, f"{response.status_code}: {msg}"
    except Exception as e:
        logger.error(f"PCM letter order exception: {e}")
        return None, str(e)


def pcm_probe(pdf_url, to_addr, from_addr):
    """Fire ONE real letter order and return PCM's raw answer. Used by
    /admin/pcm/probe to confirm credentials and a live end-to-end order
    before trusting a real campaign send to it."""
    headers, err = _pcm_auth_headers()
    if not headers:
        return {"ok": False, "detail": f"login failed: {err}", "base_url": get_pcm_base_url()}
    url = f"{get_pcm_base_url()}/order/letter"
    payload = _pcm_letter_payload(pdf_url, to_addr, from_addr, "probe:1")
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=45)
        return {"ok": r.status_code == 201, "status": r.status_code,
                "response": r.text[:4000], "sent_payload": payload,
                "base_url": get_pcm_base_url(), "test_mode": is_test_mode()}
    except Exception as e:
        return {"ok": False, "detail": str(e), "base_url": get_pcm_base_url()}


def _send_via_postgrid(pdf_bytes, to_addr, from_addr, description, idempotency_key):
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
        "addressPlacement": "top_first_page",
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
            msg = response.json().get("error", {}).get("message") or msg
        except Exception:
            pass
        logger.error(f"PostGrid invitation failed ({response.status_code}): {msg}")
        return None, f"{response.status_code}: {msg}"
    except Exception as e:
        logger.error(f"PostGrid invitation exception: {e}")
        return None, str(e)


def send_invitation_letter(pdf_bytes, to_addr, from_addr, description, idempotency_key, pdf_url=None):
    """
    Mail one invitation. Returns (provider_letter_id, None) or (None, error).
    to_addr/from_addr: {name, company, line1, line2, city, state, zip}

    idempotency_key is per-invitation ("invite:{id}"), so a retried batch
    cannot print the same letter twice — PostGrid honors it as a header, PCM
    carries it as extRefNbr on the order and on every webhook about it.

    pdf_url: a public URL PCM can fetch the exact artwork from. Required
    when the PCM provider is in effect (PCM's letter field takes a URL or
    raw HTML, never a binary/base64 upload) — see app/prospect.py's
    /a/{slug}/i/{token}/pdf route, which is what campaign_engine passes here.
    PostGrid ignores it and uses pdf_bytes directly.
    """
    if get_mail_provider() == "pcm":
        return _send_via_pcm(pdf_url, to_addr, from_addr, idempotency_key)
    return _send_via_postgrid(pdf_bytes, to_addr, from_addr, description, idempotency_key)
