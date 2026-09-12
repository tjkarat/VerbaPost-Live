"""
Prospect acquisition path — advisor-branded free letter.

The advisor hands out (or mails / QR-codes) a link to their page. A prospect
enters their name, phone and the recipient's address, gives express written
consent, and we call them so they can record a story for that person. The
story is transcribed and mailed as a keepsake letter with the advisor's name
on the envelope. The prospect is the storyteller; there is no login.

GET  /a/{slug}                 advisor-branded landing page + intake form
GET  /a/{slug}/i/{token}       same page reached from a mailed invitation's personal
                               link/QR — greets them by name and attributes the response
GET  /a/{slug}/photo           advisor photo (served from the DB)
GET  /a/{slug}/i/{token}/pdf   the invitation PDF itself — unauthenticated, on purpose:
                               PCM's mail API fetches artwork by URL, and this token
                               is already the whole security model of the personal link
POST /a/{slug}                 intake: validate -> consent record -> DNC scrub -> dial
GET  /a/{slug}/thanks/{id}     "your phone will ring" page (session-bound)
POST /a/{slug}/again/{id}      re-dial if the prospect missed the call (max 3)
GET  /a/{slug}/opt-out         one-click revoke: adds the number to the internal DNC list

Abuse controls (every submission costs a Twilio call and a letter credit):
    honeypot field, per-IP rate limit, one letter per phone per advisor per
    90 days, and the advisor's letter balance (page closes at zero).
"""

import base64
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

import ai_engine
import audit_engine
import campaign_engine
import database
import dnc_engine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/a")

MAX_CALL_ATTEMPTS = 3
REDIAL_COOLDOWN_SECONDS = 90
RATE_LIMIT_PER_IP = 5            # intakes per window
RATE_LIMIT_WINDOW_SECONDS = 3600

US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI", "ID", "IL", "IN", "IA",
    "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM",
    "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA",
    "WV", "WI", "WY", "PR", "VI", "GU", "AS", "MP", "AA", "AE", "AP",
}

# Dropdown on the intake form (mobile users found a free-text "ST" box unclear)
STATE_NAMES = [
    ("AL", "Alabama"), ("AK", "Alaska"), ("AZ", "Arizona"), ("AR", "Arkansas"), ("CA", "California"),
    ("CO", "Colorado"), ("CT", "Connecticut"), ("DE", "Delaware"), ("DC", "District of Columbia"),
    ("FL", "Florida"), ("GA", "Georgia"), ("HI", "Hawaii"), ("ID", "Idaho"), ("IL", "Illinois"),
    ("IN", "Indiana"), ("IA", "Iowa"), ("KS", "Kansas"), ("KY", "Kentucky"), ("LA", "Louisiana"),
    ("ME", "Maine"), ("MD", "Maryland"), ("MA", "Massachusetts"), ("MI", "Michigan"), ("MN", "Minnesota"),
    ("MS", "Mississippi"), ("MO", "Missouri"), ("MT", "Montana"), ("NE", "Nebraska"), ("NV", "Nevada"),
    ("NH", "New Hampshire"), ("NJ", "New Jersey"), ("NM", "New Mexico"), ("NY", "New York"),
    ("NC", "North Carolina"), ("ND", "North Dakota"), ("OH", "Ohio"), ("OK", "Oklahoma"), ("OR", "Oregon"),
    ("PA", "Pennsylvania"), ("RI", "Rhode Island"), ("SC", "South Carolina"), ("SD", "South Dakota"),
    ("TN", "Tennessee"), ("TX", "Texas"), ("UT", "Utah"), ("VT", "Vermont"), ("VA", "Virginia"),
    ("WA", "Washington"), ("WV", "West Virginia"), ("WI", "Wisconsin"), ("WY", "Wyoming"),
    ("PR", "Puerto Rico"), ("VI", "U.S. Virgin Islands"), ("GU", "Guam"),
    ("AA", "Armed Forces Americas (AA)"), ("AE", "Armed Forces Europe (AE)"), ("AP", "Armed Forces Pacific (AP)"),
]

# Post/Redirect/Get message codes (never echo raw user input in URLs)
MESSAGES = {
    "bad_name": "Please enter your name.",
    "bad_phone": "Please enter a valid US phone number.",
    "bad_recipient": "Please enter the recipient's name and full mailing address.",
    "bad_state": "Please use a two-letter state code (e.g., TN).",
    "bad_zip": "Please enter a valid ZIP code.",
    "no_consent": "Please check the consent box so we may call you.",
    "rate": "Too many requests from this connection. Please try again later.",
    "dupe": "A letter has already been requested from this phone number. If you missed our call, use the link on your confirmation page.",
    "closed": "This offer is currently closed. Please check back with your advisor.",
    "call_fail": "We couldn't place the call just now. Please try again in a moment.",
    "cooldown": "Please wait a minute or two before asking us to call again.",
    "max_attempts": "We've tried to reach you a few times. Please ask your advisor to reset the request.",
    "opted_out": "Understood — that number will not be called.",
}

# --- per-IP rate limit (per process; good enough to blunt a script) ---
_hits: dict = {}


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _rate_limited(ip: str) -> bool:
    now = time.time()
    window = [t for t in _hits.get(ip, []) if now - t < RATE_LIMIT_WINDOW_SECONDS]
    if len(window) >= RATE_LIMIT_PER_IP:
        _hits[ip] = window
        return True
    window.append(now)
    _hits[ip] = window
    return False


def _owns(request: Request, letter_id) -> bool:
    return str(letter_id) in [str(x) for x in request.session.get("prospect_ids", [])]


def _remember(request: Request, letter_id):
    ids = [str(x) for x in request.session.get("prospect_ids", [])]
    ids.append(str(letter_id))
    request.session["prospect_ids"] = ids[-10:]


def _page_or_404(request: Request, slug: str):
    from app.main import templates
    page = database.get_advisor_page_by_slug(slug)
    if not page or not page.get("active", True):
        return None, templates.TemplateResponse(
            request, "coming_soon.html",
            {"title": "Page not found",
             "detail": "This advisor page isn't available. Check the link you were given."},
            status_code=404)
    return page, None


def _render_page(request: Request, page: dict, **extra):
    from app.main import templates
    available = database.prospect_letters_available(page["advisor_email"])
    code = request.query_params.get("m")
    ctx = {
        "page": page,
        "advisor_name": page.get("display_name"),
        "firm_name": page.get("firm_name") or "",
        "has_photo": bool(page.get("photo_data")),
        "open": available > 0,
        "consent_text": dnc_engine.consent_text_for(page.get("display_name"), page.get("firm_name")),
        "consent_version": dnc_engine.CONSENT_VERSION,
        "error": MESSAGES.get(code),
        "form": {},
        "states": STATE_NAMES,
        "invitation": None,
    }
    ctx.update(extra)
    return templates.TemplateResponse(request, "prospect.html", ctx)


# ============================================================
# Landing page
# ============================================================

@router.get("/{slug}", response_class=HTMLResponse)
def landing(request: Request, slug: str):
    page, err = _page_or_404(request, slug)
    if err:
        return err
    return _render_page(request, page)


@router.get("/{slug}/i/{token}", response_class=HTMLResponse)
def landing_from_invitation(request: Request, slug: str, token: str):
    """The personal link printed on a mailed invitation. Same page and same
    intake; it just knows who was mailed, so it can greet them by name and
    tie the response back to the campaign."""
    page, err = _page_or_404(request, slug)
    if err:
        return err
    inv = database.get_invitation_by_token(token)
    if not inv or inv.get("advisor_email") != page["advisor_email"]:
        # Bad or foreign token — never a dead end, just the ordinary page.
        return RedirectResponse(f"/a/{slug}", status_code=302)
    # Remember it for the POST; the form itself carries the token too.
    request.session["invite_token"] = inv["token"]
    return _render_page(request, page, invitation=inv,
                        form={"prospect_name": inv.get("full_name") or ""})


@router.get("/{slug}/i/{token}/pdf")
def invitation_pdf(slug: str, token: str):
    """Serves the exact PDF mailed to this one person. No auth: this is the
    URL PCM's DirectMail API fetches the artwork from (their `letter` field
    takes a URL, never a binary upload — see mailer.py), and the token is
    already unguessable and single-purpose, same as the personal link itself.
    Regenerated on the fly rather than stored, so it always matches what
    campaign_engine.build_invitation_pdf produces."""
    inv = database.get_invitation_by_token(token)
    if not inv:
        return Response(status_code=404)
    page = database.get_advisor_page_by_slug(slug)
    if not page or page.get("advisor_email") != inv.get("advisor_email"):
        return Response(status_code=404)
    base_url = os.environ.get("BASE_URL", "https://app.verbapost.com").rstrip("/")
    pdf = campaign_engine.build_invitation_pdf(page, inv, base_url)
    if not pdf:
        return Response(status_code=500)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="invitation_{token}.pdf"'})


@router.get("/{slug}/photo")
def photo(slug: str):
    page = database.get_advisor_page_by_slug(slug)
    if not page or not page.get("photo_data"):
        return Response(status_code=404)
    try:
        data = base64.b64decode(page["photo_data"])
    except Exception:
        return Response(status_code=404)
    return Response(content=data, media_type=page.get("photo_mime") or "image/jpeg",
                    headers={"Cache-Control": "public, max-age=3600"})


# ============================================================
# Intake -> consent -> DNC -> dial
# ============================================================

@router.post("/{slug}", response_class=HTMLResponse)
def intake(request: Request, slug: str,
           prospect_name: str = Form(""), phone: str = Form(""),
           recipient_name: str = Form(""), line1: str = Form(""), city: str = Form(""),
           state: str = Form(""), zip_code: str = Form(""),
           consent: str = Form(""), consent_version: str = Form(""),
           website: str = Form(""), invite_token: str = Form("")):
    page, err = _page_or_404(request, slug)
    if err:
        return err
    advisor_email = page["advisor_email"]

    # Honeypot: real people never fill "website"; bots do. Pretend success.
    if website.strip():
        logger.warning(f"Honeypot tripped on /a/{slug}")
        return RedirectResponse(f"/a/{slug}?m=closed", status_code=303)

    ip = _client_ip(request)
    if _rate_limited(ip):
        return RedirectResponse(f"/a/{slug}?m=rate", status_code=303)

    # --- validation (the intake is deliberately tiny; all of it is required) ---
    prospect_name = prospect_name.strip()[:120]
    recipient_name = recipient_name.strip()[:120]
    line1 = line1.strip()[:120]
    city = city.strip()[:80]
    state = state.strip().upper()[:2]
    zip_code = zip_code.strip()[:10]
    phone_e164 = dnc_engine.normalize_phone(phone)

    if len(prospect_name) < 2:
        return RedirectResponse(f"/a/{slug}?m=bad_name", status_code=303)
    if not phone_e164:
        return RedirectResponse(f"/a/{slug}?m=bad_phone", status_code=303)
    if len(recipient_name) < 2 or len(line1) < 3 or len(city) < 2:
        return RedirectResponse(f"/a/{slug}?m=bad_recipient", status_code=303)
    if state not in US_STATES:
        return RedirectResponse(f"/a/{slug}?m=bad_state", status_code=303)
    zip_digits = "".join(ch for ch in zip_code if ch.isdigit())
    if len(zip_digits) not in (5, 9):
        return RedirectResponse(f"/a/{slug}?m=bad_zip", status_code=303)
    if consent != "yes" or consent_version != dnc_engine.CONSENT_VERSION:
        return RedirectResponse(f"/a/{slug}?m=no_consent", status_code=303)

    # --- capacity + dedupe ---
    if database.prospect_letters_available(advisor_email) <= 0:
        return RedirectResponse(f"/a/{slug}?m=closed", status_code=303)
    if database.find_recent_prospect_by_phone(advisor_email, phone_e164):
        return RedirectResponse(f"/a/{slug}?m=dupe", status_code=303)

    # --- invitation attribution (posted token wins; session is the fallback) ---
    token = (invite_token or request.session.get("invite_token") or "").strip()
    invitation = database.get_invitation_by_token(token) if token else None
    if invitation and invitation.get("advisor_email") != advisor_email:
        invitation = None

    # --- consent record (write BEFORE the scrub and the dial) ---
    now = datetime.utcnow()
    letter_id = database.create_prospect_letter(
        advisor_email=advisor_email, page_id=page.get("id"),
        prospect_name=prospect_name, prospect_phone=phone_e164,
        recipient_name=recipient_name, recipient_line1=line1, recipient_city=city,
        recipient_state=state, recipient_zip=zip_code,
        consent_version=dnc_engine.CONSENT_VERSION,
        consent_text=dnc_engine.consent_text_for(page.get("display_name"), page.get("firm_name")),
        consent_at=now, consent_ip=ip,
        consent_user_agent=(request.headers.get("user-agent") or "")[:300],
        status="consented", call_attempts=0,
        invitation_id=(invitation or {}).get("id"))
    if not letter_id:
        return RedirectResponse(f"/a/{slug}?m=call_fail", status_code=303)
    _remember(request, letter_id)
    if invitation:
        database.mark_invitation_responded(invitation["id"], letter_id)
    audit_engine.log_event(advisor_email, "Prospect Consent Captured",
                           metadata={"letter_id": letter_id, "phone_last4": phone_e164[-4:], "ip": ip,
                                     "invitation_id": (invitation or {}).get("id")})

    # --- DNC scrub before dialing ---
    scrub = dnc_engine.scrub(phone_e164)
    database.update_prospect_letter(letter_id, dnc_status=scrub["status"],
                                    dnc_provider=scrub["provider"], dnc_checked_at=scrub["checked_at"])
    if not dnc_engine.may_dial(scrub):
        database.update_prospect_letter(letter_id, status="dnc_blocked")
        audit_engine.log_event(advisor_email, "Prospect DNC Blocked",
                               metadata={"letter_id": letter_id, "dnc": scrub["status"]})
        return RedirectResponse(f"/a/{slug}/thanks/{letter_id}", status_code=303)

    # --- dial ---
    _place_call(page, letter_id, phone_e164, prospect_name, recipient_name)
    return RedirectResponse(f"/a/{slug}/thanks/{letter_id}", status_code=303)


def _place_call(page: dict, letter_id, phone_e164, prospect_name, recipient_name):
    """Shared by intake and re-dial. Returns True if Twilio accepted the call."""
    sid, err = ai_engine.trigger_prospect_call(
        to_phone=phone_e164, prospect_name=prospect_name,
        advisor_name=page.get("display_name"), firm_name=page.get("firm_name"),
        recipient_name=recipient_name, question_text=page.get("prompt"),
        letter_id=letter_id)
    current = database.get_prospect_letter(letter_id) or {}
    attempts = int(current.get("call_attempts") or 0) + 1
    if not sid:
        logger.error(f"Prospect call failed for letter {letter_id}: {err}")
        database.update_prospect_letter(letter_id, call_attempts=attempts,
                                        last_call_at=datetime.utcnow(), status="call_failed")
        return False
    database.update_prospect_letter(letter_id, call_sid=sid, call_attempts=attempts,
                                    last_call_at=datetime.utcnow(), status="calling")
    audit_engine.log_event(page["advisor_email"], "Prospect Call Placed",
                           metadata={"letter_id": letter_id, "sid": sid, "attempt": attempts})
    return True


# ============================================================
# Confirmation + re-dial
# ============================================================

@router.get("/{slug}/thanks/{letter_id}", response_class=HTMLResponse)
def thanks(request: Request, slug: str, letter_id: int):
    from app.main import templates
    page, err = _page_or_404(request, slug)
    if err:
        return err
    if not _owns(request, letter_id):
        return RedirectResponse(f"/a/{slug}", status_code=302)
    letter = database.get_prospect_letter(letter_id)
    if not letter or letter.get("advisor_email") != page["advisor_email"]:
        return RedirectResponse(f"/a/{slug}", status_code=302)
    code = request.query_params.get("m")
    return templates.TemplateResponse(request, "prospect_thanks.html", {
        "page": page, "letter": letter, "slug": slug,
        "advisor_name": page.get("display_name"), "firm_name": page.get("firm_name") or "",
        "from_number": ai_engine.get_secret("twilio.from_number") or "+16156567667",
        "can_redial": letter.get("status") in ("calling", "call_failed", "recording_too_short")
                      and int(letter.get("call_attempts") or 0) < MAX_CALL_ATTEMPTS,
        "error": MESSAGES.get(code),
    })


@router.post("/{slug}/again/{letter_id}")
def call_again(request: Request, slug: str, letter_id: int):
    page, err = _page_or_404(request, slug)
    if err:
        return err
    if not _owns(request, letter_id):
        return RedirectResponse(f"/a/{slug}", status_code=302)
    letter = database.get_prospect_letter(letter_id)
    if not letter or letter.get("advisor_email") != page["advisor_email"]:
        return RedirectResponse(f"/a/{slug}", status_code=302)
    if letter.get("status") not in ("calling", "call_failed", "recording_too_short"):
        return RedirectResponse(f"/a/{slug}/thanks/{letter_id}", status_code=303)
    if int(letter.get("call_attempts") or 0) >= MAX_CALL_ATTEMPTS:
        return RedirectResponse(f"/a/{slug}/thanks/{letter_id}?m=max_attempts", status_code=303)
    last = letter.get("last_call_at")
    if isinstance(last, datetime) and datetime.utcnow() - last < timedelta(seconds=REDIAL_COOLDOWN_SECONDS):
        return RedirectResponse(f"/a/{slug}/thanks/{letter_id}?m=cooldown", status_code=303)
    # Consent + scrub already on file for this number; re-check the internal
    # list in case they opted out between attempts.
    scrub = dnc_engine.scrub(letter["prospect_phone"])
    if not dnc_engine.may_dial(scrub):
        database.update_prospect_letter(letter_id, status="dnc_blocked", dnc_status=scrub["status"],
                                        dnc_checked_at=scrub["checked_at"])
        return RedirectResponse(f"/a/{slug}/thanks/{letter_id}", status_code=303)
    ok = _place_call(page, letter_id, letter["prospect_phone"],
                     letter["prospect_name"], letter["recipient_name"])
    return RedirectResponse(f"/a/{slug}/thanks/{letter_id}" + ("" if ok else "?m=call_fail"),
                            status_code=303)


@router.post("/{slug}/opt-out/{letter_id}")
def opt_out(request: Request, slug: str, letter_id: int):
    """Revoke consent from the confirmation page: number goes on the internal
    DNC list and the request is closed. No further dials, ever."""
    page, err = _page_or_404(request, slug)
    if err:
        return err
    if not _owns(request, letter_id):
        return RedirectResponse(f"/a/{slug}", status_code=302)
    letter = database.get_prospect_letter(letter_id)
    if letter and letter.get("advisor_email") == page["advisor_email"]:
        dnc_engine.opt_out(letter["prospect_phone"], reason="prospect revoked consent",
                           added_by=f"letter:{letter_id}")
        if letter.get("status") in ("consented", "calling", "call_failed"):
            database.update_prospect_letter(letter_id, status="opted_out")
        audit_engine.log_event(page["advisor_email"], "Prospect Opted Out",
                               metadata={"letter_id": letter_id})
    return RedirectResponse(f"/a/{slug}/thanks/{letter_id}?m=opted_out", status_code=303)


# ============================================================
# Recording -> letter (called from the Twilio webhook background task)
# ============================================================

LETTER_VERSION = "prospect-v1"
MIN_TRANSCRIPT_CHARS = 40          # shorter than this is a voicemail greeting or a hang-up
PLACEHOLDER_TRANSCRIPT = "[Audio captured. Transcription unavailable.]"


def finalize_recording(letter_id):
    """
    The recording is on file (status 'recorded'). Polish the transcript,
    consume ONE letter credit, and queue for print. Order matters — the
    artifact is secured before the ledger is touched (financial atomicity).
    Returns the new status.
    """
    import email_engine

    letter = database.get_prospect_letter(letter_id)
    if not letter or letter.get("status") != "recorded":
        return (letter or {}).get("status")

    raw = (letter.get("transcript_raw") or "").strip()
    if raw == PLACEHOLDER_TRANSCRIPT or len(raw) < MIN_TRANSCRIPT_CHARS:
        # Nothing worth printing — no credit consumed; prospect may re-dial.
        database.update_prospect_letter(letter_id, status="recording_too_short")
        audit_engine.log_event(letter["advisor_email"], "Prospect Recording Too Short",
                               metadata={"letter_id": letter_id, "chars": len(raw)})
        return "recording_too_short"

    polished = ai_engine.refine_text(raw) or raw
    now = datetime.utcnow()
    database.update_prospect_letter(letter_id, letter_text=polished, letter_version=LETTER_VERSION,
                                    status="Approved", queued_at=now)
    # NOTE: no ledger write here. The billable unit is the INVITATION mailed
    # (campaign_engine consumes one credit per PostGrid-accepted letter); the
    # story letter a responder earns is included in that price. The landing
    # page is gated by database.prospect_story_allowance instead, so a link
    # shared beyond the mailing can't produce unlimited free stories.
    audit_engine.log_event(letter["advisor_email"], "Prospect Letter Queued",
                           metadata={"letter_id": letter_id, "chars": len(polished)})

    page = database.get_advisor_page_by_email(letter["advisor_email"]) or {}
    recipient = {"name": letter["recipient_name"], "street": letter["recipient_line1"],
                 "city": letter["recipient_city"], "state": letter["recipient_state"],
                 "zip_code": letter["recipient_zip"]}
    try:
        email_engine.send_admin_print_ready_alert(
            user_email=f"prospect:{letter['advisor_email']}", draft_id=f"p{letter_id}",
            content_preview=polished[:500], mailing_list=[recipient])
    except Exception as e:
        logger.error(f"Admin print alert failed for prospect letter {letter_id}: {e}")
    try:
        # First sentence or so — enough for the advisor to feel what was
        # said before they decide whether today is the day to call back.
        excerpt = polished.strip()
        if len(excerpt) > 220:
            cut = excerpt.rfind(" ", 0, 220)
            excerpt = excerpt[:cut if cut > 0 else 220].rstrip() + "…"
        email_engine.send_advisor_prospect_letter_alert(
            advisor_email=letter["advisor_email"], advisor_name=page.get("display_name") or "there",
            prospect_name=letter["prospect_name"], recipient_name=letter["recipient_name"],
            letters_left=database.prospect_credit_balance(letter["advisor_email"]),  # invitations left
            excerpt=excerpt)
    except Exception as e:
        logger.error(f"Advisor alert failed for prospect letter {letter_id}: {e}")
    return "Approved"
