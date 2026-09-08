"""
DNC scrub + consent record for the prospect acquisition path.

Every outbound prospect call passes through scrub() first. Two layers:

  1. INTERNAL suppression list (dnc_suppressions table) — opt-outs,
     complaints, wrong numbers. Always checked. Always wins.
  2. EXTERNAL provider — optional, driven entirely by env vars so a vendor
     can be plugged in without a code change:

        DNC_PROVIDER_NAME   label written to the send log (e.g. "dnc.com")
        DNC_PROVIDER_URL    endpoint; "{phone}" in the URL is replaced with
                            the E.164 number (GET) — otherwise the number is
                            POSTed as JSON {"phone": "+1..."}
        DNC_PROVIDER_KEY    sent as  Authorization: Bearer <key>
        DNC_PROVIDER_RESULT_KEY  JSON key holding the listed flag (default
                            "on_dnc"); truthy => number is on a DNC list
        DNC_FAIL_CLOSED     "1" (default) blocks the dial if the provider
                            errors; "0" proceeds on the consent record alone

Until a provider is configured the scrub records status "internal_only",
which is honest: the number was checked against OUR list, not the
national registry. Express written consent (captured at intake) is the
legal basis for the call either way — the scrub is belt-and-braces.

Statuses written to prospect_letters.dnc_status:
    clear          checked internal + external, not listed
    internal_only  checked internal list only (no provider configured)
    listed         on a DNC list — do NOT dial
    error          provider failed — dial only if DNC_FAIL_CLOSED=0
"""

import logging
import os
import re
from datetime import datetime

import requests

try:
    import database
except ImportError:  # pragma: no cover
    database = None

logger = logging.getLogger(__name__)

# ------------------------------------------------------------
# Express written consent — the exact text shown next to the checkbox.
# Bump the version whenever the wording changes; the send log stores both
# the version and the full text so the record stands on its own.
# ------------------------------------------------------------
CONSENT_VERSION = "2026-09-v1"
CONSENT_TEXT = (
    "By checking this box and submitting, I give my express written consent "
    "for VerbaPost, on behalf of {advisor_name}{firm_clause}, to place a call "
    "to the phone number I entered, using an automated system and a "
    "pre-recorded or artificial voice, so that I can record a story. I "
    "understand the call will be recorded and transcribed, that a printed "
    "letter containing my story will be mailed to the recipient I named, and "
    "that consent is not a condition of any purchase. Message and data rates "
    "do not apply to this call. I may revoke consent at any time."
)


def consent_text_for(advisor_name, firm_name=None):
    firm_clause = f" of {firm_name}" if firm_name else ""
    return CONSENT_TEXT.format(advisor_name=advisor_name or "your advisor",
                               firm_clause=firm_clause)


# ------------------------------------------------------------
# Phone normalization (US/CA only for now — Twilio from-number is US)
# ------------------------------------------------------------
_DIGITS = re.compile(r"\d")


def normalize_phone(raw):
    """Return E.164 (+1NNNNNNNNNN) or None if it can't be a NANP number."""
    if not raw:
        return None
    digits = "".join(_DIGITS.findall(str(raw)))
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        return None
    # NANP: area code and exchange can't start with 0 or 1
    if digits[0] in "01" or digits[3] in "01":
        return None
    return "+1" + digits


# ------------------------------------------------------------
# The scrub
# ------------------------------------------------------------

def _provider_config():
    url = (os.environ.get("DNC_PROVIDER_URL") or "").strip()
    if not url:
        return None
    return {
        "name": (os.environ.get("DNC_PROVIDER_NAME") or "external").strip(),
        "url": url,
        "key": (os.environ.get("DNC_PROVIDER_KEY") or "").strip(),
        "result_key": (os.environ.get("DNC_PROVIDER_RESULT_KEY") or "on_dnc").strip(),
    }


def fail_closed():
    return (os.environ.get("DNC_FAIL_CLOSED") or "1").strip() != "0"


def _check_external(phone_e164, cfg):
    """Returns True (listed), False (clear). Raises on any failure."""
    headers = {"Accept": "application/json"}
    if cfg["key"]:
        headers["Authorization"] = f"Bearer {cfg['key']}"
    if "{phone}" in cfg["url"]:
        resp = requests.get(cfg["url"].replace("{phone}", phone_e164), headers=headers, timeout=8)
    else:
        resp = requests.post(cfg["url"], json={"phone": phone_e164}, headers=headers, timeout=8)
    resp.raise_for_status()
    data = resp.json()
    # tolerate one level of nesting: {"result": {"on_dnc": true}}
    if cfg["result_key"] not in data and isinstance(data.get("result"), dict):
        data = data["result"]
    if cfg["result_key"] not in data:
        raise ValueError(f"provider response missing '{cfg['result_key']}'")
    return bool(data[cfg["result_key"]])


def scrub(phone_e164):
    """
    Returns a dict for the send log:
        {"status": clear|internal_only|listed|error,
         "provider": str, "checked_at": datetime, "detail": str}
    """
    now = datetime.utcnow()
    result = {"status": "internal_only", "provider": "internal", "checked_at": now, "detail": ""}

    # 1. Internal list — a DB failure here is an error, never a "clear".
    try:
        if database and database.is_dnc_suppressed(phone_e164):
            result.update(status="listed", detail="internal suppression list")
            return result
    except Exception as e:
        logger.error(f"Internal DNC check failed for {phone_e164[-4:]}: {e}")
        result.update(status="error", detail=f"internal list unavailable: {e}")
        return result

    # 2. External provider (optional)
    cfg = _provider_config()
    if not cfg:
        return result
    result["provider"] = f"internal+{cfg['name']}"
    try:
        listed = _check_external(phone_e164, cfg)
        result.update(status="listed" if listed else "clear",
                      detail=f"{cfg['name']} says {'listed' if listed else 'clear'}")
    except Exception as e:
        logger.error(f"External DNC check failed ({cfg['name']}): {e}")
        result.update(status="error", detail=f"{cfg['name']} error: {e}")
    return result


def may_dial(scrub_result):
    """Policy: listed never dials; error dials only when fail-open."""
    status = (scrub_result or {}).get("status")
    if status in ("clear", "internal_only"):
        return True
    if status == "error":
        return not fail_closed()
    return False


def opt_out(phone_e164, reason="opt-out", added_by="system"):
    """Add a number to the internal list (STOP requests, complaints)."""
    if not database:
        return False
    return database.add_dnc_suppression(phone_e164, reason=reason, added_by=added_by)
