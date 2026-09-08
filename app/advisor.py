"""
Advisor Portal — Phase 3 port of ui_advisor.py.

GET  /advisor                    dashboard (credits, activate, roster, media locker)
POST /advisor/firm               update firm branding
POST /advisor/activate           sponsor a client (deduct 1 credit, welcome email)
POST /advisor/resend             resend welcome email
POST /advisor/release/{pid}      toggle media release for heirs
GET  /advisor/checkout           create Stripe session ($99 credit) and redirect
"""

import base64
import csv
import io
import logging
from datetime import datetime
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import APIRouter, BackgroundTasks, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response, StreamingResponse

import audit_engine
import campaign_engine
import database
import email_engine
import invitation_format
import mailer
import payment_engine
import pricing_engine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/advisor")


def _require_advisor(request: Request):
    """Return (email, profile) or None if not authorized."""
    email = request.session.get("email")
    if not email:
        return None
    profile = database.get_user_profile(email) or {}
    return email, profile


def _render(request: Request, email: str, profile: dict, **extra):
    from app.main import templates
    ctx = {
        "email": email,
        "firm_name": profile.get("advisor_firm") or "",
        "advisor_name": profile.get("full_name") or email,
        "credits": profile.get("credits", 0) or 0,
        # Roster reads the clients table — the table activation actually
        # writes to. (fetch_advisor_clients read user_profiles.created_by,
        # which is never set for heirs who already had an account.)
        "clients": database.get_advisor_clients(email),
        "projects": database.get_advisor_projects_for_media(email),
        "error": None, "notice": None,
        # populated only right after a list upload (the review screen)
        "review_campaign": None, "review_rows": [], "review_problems": [], "review_mapping": {},
    }
    ctx.update(_campaign_ctx(email, profile))
    ctx.update(extra)
    return templates.TemplateResponse(request, "advisor.html", ctx)


def _campaign_ctx(email: str, profile: dict):
    """Prospect acquisition path: page config, invitation balance, mailings."""
    page = database.get_advisor_page_by_email(email) or {}
    prior = database.prospect_has_prior_purchase(email)
    base = os.environ.get("BASE_URL", "https://app.verbapost.com").rstrip("/")
    mailings = database.list_campaigns(email)
    responses = len(database.list_prospect_letters(advisor_email=email)) if (page or prior) else 0
    return {
        "campaign": page,
        "campaign_url": f"{base}/a/{page['slug']}" if page.get("slug") else None,
        "campaign_balance": database.prospect_credit_balance(email) if (page or prior) else 0,
        "campaign_has_prior": prior,
        "campaign_quote": pricing_engine.prospect_quote(prior),
        "mailings": mailings,
        "mailed_total": sum(m.get("sent_count") or 0 for m in mailings),
        "response_total": responses,
        "postgrid_test_mode": mailer.is_test_mode(),
        "letter_price": pricing_engine.PROSPECT_LETTER_PRICE_CENTS // 100,
        "first_campaign_price": pricing_engine.FIRST_CAMPAIGN_PRICE_CENTS // 100,
        "first_campaign_letters": pricing_engine.FIRST_CAMPAIGN_LETTERS,
        "repeat_max": pricing_engine.REPEAT_MAX_LETTERS,
        "max_rows": campaign_engine.MAX_ROWS_PER_UPLOAD,
        "default_slug": _suggest_slug(profile.get("full_name") or email.split("@")[0]),
    }


def _suggest_slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return slug[:40] or "advisor"


@router.get("", response_class=HTMLResponse)
def dashboard(request: Request):
    auth = _require_advisor(request)
    if not auth:
        return RedirectResponse("/login", status_code=302)
    email, profile = auth
    notice = None
    if request.query_params.get("purchased"):
        notice = "Payment received — your credit will appear within a minute. Refresh if needed."
    return _render(request, email, profile, notice=notice)


@router.post("/firm", response_class=HTMLResponse)
def update_firm(request: Request, firm_name: str = Form(...)):
    auth = _require_advisor(request)
    if not auth:
        return RedirectResponse("/login", status_code=302)
    email, profile = auth
    name = firm_name.strip()
    if not name:
        return _render(request, email, profile, error="Firm name cannot be empty.")
    database.update_advisor_firm_name(email, name)
    profile["advisor_firm"] = name
    return _render(request, email, profile, notice="Branding updated.")


@router.post("/activate", response_class=HTMLResponse)
def activate_client(request: Request, client_name: str = Form(...),
                    client_email: str = Form(...)):
    auth = _require_advisor(request)
    if not auth:
        return RedirectResponse("/login", status_code=302)
    email, profile = auth
    credits = profile.get("credits", 0) or 0
    firm = profile.get("advisor_firm") or "Your Advisor"

    if credits < 1:
        return _render(request, email, profile,
                       error="Insufficient credits. Purchase a credit first ($99).")
    if not client_name.strip() or "@" not in client_email:
        return _render(request, email, profile,
                       error="Client name and a valid email are required.")

    ok, msg = database.create_sponsored_user(
        advisor_email=email, client_name=client_name.strip(),
        client_email=client_email.strip().lower(), client_phone="",
        advisor_firm=firm)
    if not ok:
        return _render(request, email, profile, error=f"Activation failed: {msg}")

    database.update_user_credits(email, credits - 1)
    profile["credits"] = credits - 1
    # The $99 engagement INCLUDES one story: grant the family's first
    # story credit at activation (heir-side credits = story balance).
    database.add_advisor_credit(client_email.strip().lower(), 1)
    sent = email_engine.send_heir_welcome_email(
        to_email=client_email.strip().lower(), advisor_firm=firm,
        advisor_name=profile.get("full_name") or "Your Advisor",
        heir_name=client_name.strip())
    audit_engine.log_event(email, "Client Activated",
                           metadata={"client_email": client_email, "credit_spent": 1})
    if sent:
        return _render(request, email, profile,
                       notice=f"Welcome email sent to {client_email}. "
                              "They can now log in and schedule the interview.")
    return _render(request, email, profile,
                   notice="Client created, but the email failed to send — "
                          "use Resend in the roster below.")


@router.post("/resend", response_class=HTMLResponse)
def resend_invite(request: Request, client_email: str = Form(...)):
    auth = _require_advisor(request)
    if not auth:
        return RedirectResponse("/login", status_code=302)
    email, profile = auth
    sent = email_engine.send_heir_welcome_email(
        to_email=client_email, advisor_firm=profile.get("advisor_firm") or "Your Advisor",
        advisor_name=profile.get("full_name") or "Your Advisor")
    if sent:
        return _render(request, email, profile, notice=f"Invite re-sent to {client_email}.")
    return _render(request, email, profile, error="Failed to send. Check email configuration.")


@router.post("/release/{pid}", response_class=HTMLResponse)
def toggle_release(request: Request, pid: int, release: str = Form("on")):
    auth = _require_advisor(request)
    if not auth:
        return RedirectResponse("/login", status_code=302)
    email, profile = auth
    # Ownership check: an advisor may only release audio on their own projects
    owned = {str(p.get("id")) for p in database.get_advisor_projects_for_media(email)}
    if str(pid) not in owned:
        return RedirectResponse("/advisor", status_code=303)
    database.toggle_media_release(pid, release == "on")
    return RedirectResponse("/advisor", status_code=303)


@router.get("/story/checkout")
def buy_additional_story(request: Request, client_email: str = ""):
    """$40 — commission an additional story for an EXISTING client family.
    The advisor pays; the webhook credits the family's story balance."""
    auth = _require_advisor(request)
    if not auth:
        return RedirectResponse("/login", status_code=302)
    email, _profile = auth
    target = (client_email or "").strip().lower()
    if "@" not in target:
        return RedirectResponse("/advisor", status_code=302)
    url = payment_engine.create_checkout_session(
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {
                    "name": "Additional Legacy Story",
                    "description": f"One additional interview & keepsake letters for {target}",
                },
                "unit_amount": 4000,
            },
            "quantity": 1,
        }],
        user_email=target,      # fulfillment: family's story balance
        payer_email=email,      # billing: the advisor
        mode="payment",
        success_path="/advisor",
    )
    if not url:
        return RedirectResponse("/advisor?checkout=failed", status_code=302)
    return RedirectResponse(url, status_code=303)


@router.get("/checkout")
def buy_credit(request: Request):
    auth = _require_advisor(request)
    if not auth:
        return RedirectResponse("/login", status_code=302)
    email, _profile = auth
    url = payment_engine.create_checkout_session(
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {
                    "name": "Legacy Project Credit",
                    "description": "1 Credit = 1 Family Archive",
                },
                "unit_amount": 9900,
            },
            "quantity": 1,
        }],
        user_email=email,
        mode="payment",
        success_path="/advisor",
    )
    if not url:
        return RedirectResponse("/advisor?checkout=failed", status_code=302)
    return RedirectResponse(url, status_code=303)


# ============================================================
# PROSPECT ACQUISITION PATH — page setup, letter purchase, send log
# ============================================================

SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{1,38}[a-z0-9])?$")
PHOTO_MAX_BYTES = 2 * 1024 * 1024
PHOTO_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _process_photo(data: bytes, mime: str):
    """Shrink to a 400px square JPEG when Pillow is available (fpdf2 pulls it
    in); otherwise store the upload as-is under the size cap."""
    try:
        from PIL import Image, ImageOps
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img).convert("RGB")
        img = ImageOps.fit(img, (400, 400))
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=85)
        return out.getvalue(), "image/jpeg"
    except Exception as e:
        logger.warning(f"Photo resize skipped: {e}")
        return data, mime


@router.post("/campaign/page")
async def save_campaign_page(request: Request,
                             slug: str = Form(""), display_name: str = Form(""),
                             firm_name: str = Form(""), headline: str = Form(""),
                             intro: str = Form(""), prompt: str = Form(""),
                             return_line1: str = Form(""), return_city: str = Form(""),
                             return_state: str = Form(""), return_zip: str = Form(""),
                             disclosure: str = Form(""), invite_body: str = Form(""),
                             active: str = Form("on"),
                             photo: UploadFile = File(None)):
    auth = _require_advisor(request)
    if not auth:
        return RedirectResponse("/login", status_code=302)
    email, profile = auth

    slug = slug.strip().lower()
    if not SLUG_RE.match(slug):
        return _render(request, email, profile,
                       error="Page address must be 3-40 characters: letters, numbers and dashes only.")
    if len(display_name.strip()) < 2:
        return _render(request, email, profile, error="Your display name is required.")

    fields = {
        "slug": slug, "display_name": display_name.strip()[:120],
        "firm_name": firm_name.strip()[:120] or None,
        "headline": headline.strip()[:160] or None,
        "intro": intro.strip()[:600] or None,
        "prompt": prompt.strip()[:400] or None,
        "return_line1": return_line1.strip()[:120] or None,
        "return_city": return_city.strip()[:80] or None,
        "return_state": return_state.strip().upper()[:2] or None,
        "return_zip": return_zip.strip()[:10] or None,
        "disclosure": disclosure.strip()[:600] or None,
        "invite_body": invite_body.strip()[:2000] or None,
        "active": active == "on",
    }
    if photo is not None and photo.filename:
        data = await photo.read()
        mime = (photo.content_type or "").lower()
        if mime not in PHOTO_TYPES:
            return _render(request, email, profile, error="Photo must be a JPEG, PNG or WebP image.")
        if len(data) > PHOTO_MAX_BYTES:
            return _render(request, email, profile, error="Photo must be under 2 MB.")
        data, mime = _process_photo(data, mime)
        fields["photo_data"] = base64.b64encode(data).decode("ascii")
        fields["photo_mime"] = mime

    ok, msg = database.upsert_advisor_page(email, **fields)
    if not ok:
        return _render(request, email, profile, error=msg)
    audit_engine.log_event(email, "Prospect Page Saved", metadata={"slug": slug})
    return _render(request, email, profile, notice="Your prospect page is saved.")


@router.get("/campaign/checkout")
def buy_prospect_letters(request: Request, letters: int = 0):
    """First campaign: flat $500 for 25 letters. After that: $20 per letter.
    The quote is computed server-side from the ledger — the button can't
    pick its own price."""
    auth = _require_advisor(request)
    if not auth:
        return RedirectResponse("/login", status_code=302)
    email, _profile = auth
    quote = pricing_engine.prospect_quote(database.prospect_has_prior_purchase(email), letters)
    url = payment_engine.create_checkout_session(
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {
                    "name": quote["label"],
                    "description": "Advisor-branded prospect invitations, mailed first class with a personal "
                                   "link. Includes the story letter for everyone who responds: outbound call, "
                                   "transcription, linen letter with audio QR, postage, your name on the envelope.",
                },
                "unit_amount": quote["total_cents"],
            },
            "quantity": 1,
        }],
        user_email=email,
        mode="payment",
        success_path="/advisor",
        service="prospect_letters",
        extra_metadata={"letters": str(quote["letters"]), "kind": quote["kind"]},
    )
    if not url:
        return RedirectResponse("/advisor?checkout=failed", status_code=302)
    return RedirectResponse(url, status_code=303)


CSV_COLUMNS = [
    "id", "created_at_utc", "status", "advisor_email",
    "prospect_name", "prospect_phone",
    "recipient_name", "recipient_line1", "recipient_city", "recipient_state", "recipient_zip",
    "consent_version", "consent_at_utc", "consent_ip", "consent_user_agent", "consent_text",
    "dnc_status", "dnc_provider", "dnc_checked_at_utc",
    "call_sid", "call_attempts", "last_call_at_utc", "audio_url",
    "letter_version", "queued_at_utc", "sent_at_utc", "letter_text", "transcript_raw",
    "invitation_id",
]
_CSV_SOURCE = {
    "created_at_utc": "created_at", "consent_at_utc": "consent_at",
    "dnc_checked_at_utc": "dnc_checked_at", "last_call_at_utc": "last_call_at",
    "queued_at_utc": "queued_at", "sent_at_utc": "sent_at",
}


def _csv_cell(v):
    if v is None:
        return ""
    if hasattr(v, "isoformat"):
        return v.isoformat(timespec="seconds")
    s = str(v)
    # Formula-injection guard: Excel executes cells starting with = + - @.
    # E.164 phone numbers ("+1615...") are digits only and stay as-is.
    if s and s[0] in "=+-@" and not re.match(r"^\+\d+$", s):
        s = "'" + s
    return s


def prospect_csv(rows, filename="prospect_send_log.csv"):
    """Send log -> CSV. One row per intake, every column that a records
    reviewer could ask for, including the letter text itself."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(CSV_COLUMNS)
    for r in rows:
        w.writerow([_csv_cell(r.get(_CSV_SOURCE.get(col, col))) for col in CSV_COLUMNS])
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/campaign/export.csv")
def export_send_log(request: Request):
    auth = _require_advisor(request)
    if not auth:
        return RedirectResponse("/login", status_code=302)
    email, _profile = auth
    audit_engine.log_event(email, "Prospect Send Log Exported")
    return prospect_csv(database.list_prospect_letters(advisor_email=email),
                        filename=f"prospect_send_log_{email.split('@')[0]}.csv")


# ============================================================
# INVITATION CAMPAIGNS — upload a mailing list, mail it via PostGrid
# ============================================================

CSV_MAX_BYTES = 2 * 1024 * 1024


def _base_url():
    return os.environ.get("BASE_URL", "https://app.verbapost.com").rstrip("/")


@router.post("/campaign/upload")
async def upload_mailing_list(request: Request, list_name: str = Form(""),
                              mailing_list: UploadFile = File(None)):
    """Parse the CSV and create a DRAFT mailing. Nothing is mailed and no
    credit is spent until the advisor reviews and clicks Send."""
    auth = _require_advisor(request)
    if not auth:
        return RedirectResponse("/login", status_code=302)
    email, profile = auth

    page = database.get_advisor_page_by_email(email)
    if not page or not page.get("slug"):
        return _render(request, email, profile,
                       error="Set up your prospect page first — the invitations link to it.")
    if not all(page.get(k) for k in ("return_line1", "return_city", "return_state", "return_zip")):
        return _render(request, email, profile,
                       error="Add your return address before mailing — it prints on every envelope.")
    if mailing_list is None or not mailing_list.filename:
        return _render(request, email, profile, error="Choose a CSV file to upload.")

    data = await mailing_list.read()
    if len(data) > CSV_MAX_BYTES:
        return _render(request, email, profile, error="That file is too large (2 MB maximum).")

    rows, problems, mapping = campaign_engine.parse_mailing_list(data)
    if not rows:
        detail = problems[0][1] if problems else "No usable rows found."
        return _render(request, email, profile, error=f"Couldn't read that list. {detail}")

    # Drop households this advisor has already mailed.
    already = database.previously_mailed_addresses(email)
    fresh, dupes = [], 0
    for r in rows:
        if (r["line1"].strip().lower(), r["zip_code"][:5]) in already:
            dupes += 1
        else:
            fresh.append(r)
    if not fresh:
        return _render(request, email, profile,
                       error="Every address on that list has already been mailed for you.")

    name = list_name.strip()[:80] or f"{mailing_list.filename[:60]} ({datetime.now():%b %d})"
    campaign_id = database.create_campaign(email, page.get("id"), name, fresh)
    if not campaign_id:
        return _render(request, email, profile, error="Could not save that list. Please try again.")

    audit_engine.log_event(email, "Mailing List Uploaded",
                           metadata={"campaign_id": campaign_id, "rows": len(fresh),
                                     "skipped": len(problems), "already_mailed": dupes})
    notice = f"Loaded {len(fresh)} addresses."
    if dupes:
        notice += f" {dupes} skipped (already mailed)."
    if problems:
        notice += f" {len(problems)} row(s) had problems."
    return _render(request, email, profile, notice=notice,
                   review_campaign=database.get_campaign(campaign_id, email),
                   review_rows=database.list_invitations(campaign_id=campaign_id)[:10],
                   review_problems=problems[:10], review_mapping=mapping)


@router.get("/campaign/{campaign_id}/proof.pdf")
def campaign_proof(request: Request, campaign_id: int):
    """The exact letter the first person on the list will receive."""
    auth = _require_advisor(request)
    if not auth:
        return RedirectResponse("/login", status_code=302)
    email, _profile = auth
    camp = database.get_campaign(campaign_id, email)
    if not camp:
        return Response(status_code=404)
    rows = database.list_invitations(campaign_id=campaign_id)
    if not rows:
        return Response(status_code=404)
    page = database.get_advisor_page_by_email(email) or {}
    pdf = campaign_engine.build_invitation_pdf(page, rows[0], _base_url())
    if not pdf:
        return Response(status_code=500)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="invitation_proof_{campaign_id}.pdf"'})


@router.post("/campaign/{campaign_id}/send")
def campaign_send(request: Request, campaign_id: int, background: BackgroundTasks):
    """Mail the list. Runs in the background so a 200-name list doesn't hold
    the request open; each row consumes a credit only once PostGrid accepts it."""
    auth = _require_advisor(request)
    if not auth:
        return RedirectResponse("/login", status_code=302)
    email, profile = auth
    camp = database.get_campaign(campaign_id, email)
    if not camp:
        return _render(request, email, profile, error="That mailing was not found.")
    if camp.get("status") == "sending":
        return _render(request, email, profile, error="That mailing is already going out.")

    pending = [r for r in database.list_invitations(campaign_id=campaign_id)
               if r["status"] in ("pending", "failed", "skipped")]
    if not pending:
        return _render(request, email, profile, notice="Every invitation in that mailing has already been sent.")

    balance = database.prospect_credit_balance(email)
    if balance <= 0:
        return _render(request, email, profile,
                       error="You have no invitations remaining. Buy more to send this mailing.")

    # Re-queue anything previously skipped for balance so the retry picks it up.
    for r in pending:
        if r["status"] == "skipped":
            database.update_invitation(r["id"], status="pending", skip_reason=None)

    background.add_task(campaign_engine.send_campaign, campaign_id, _base_url())
    audit_engine.log_event(email, "Mailing Send Started",
                           metadata={"campaign_id": campaign_id, "queued": len(pending), "balance": balance})
    short = min(len(pending), balance)
    notice = f"Sending {short} invitation(s) now — this page will show progress as they go out."
    if balance < len(pending):
        notice += f" {len(pending) - balance} will wait until you buy more invitations."
    if mailer.is_test_mode():
        notice = "TEST MODE (PostGrid test key): letters are created but never printed. " + notice
    return _render(request, email, profile, notice=notice)


@router.get("/campaign/{campaign_id}/rows.csv")
def campaign_rows_csv(request: Request, campaign_id: int):
    """Per-name status for one mailing: sent, failed, and who responded."""
    auth = _require_advisor(request)
    if not auth:
        return RedirectResponse("/login", status_code=302)
    email, _profile = auth
    if not database.get_campaign(campaign_id, email):
        return Response(status_code=404)
    rows = database.list_invitations(campaign_id=campaign_id)
    cols = ["id", "full_name", "line1", "line2", "city", "state", "zip_code",
            "token", "status", "skip_reason", "postgrid_id", "error",
            "sent_at", "responded_letter_id", "responded_at"]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(cols)
    for r in rows:
        w.writerow([_csv_cell(r.get(c)) for c in cols])
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="mailing_{campaign_id}.csv"'})
