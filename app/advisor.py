"""
Advisor Portal — Phase 3 port of ui_advisor.py.

GET  /advisor                    dashboard (credits, activate, roster, media locker)
POST /advisor/firm               update firm branding
POST /advisor/activate           sponsor a client (deduct 1 credit, welcome email)
POST /advisor/resend             resend welcome email
POST /advisor/release/{pid}      toggle media release for heirs
GET  /advisor/checkout           create Stripe session ($99 credit) and redirect
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

import audit_engine
import database
import email_engine
import payment_engine

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
    }
    ctx.update(extra)
    return templates.TemplateResponse(request, "advisor.html", ctx)


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
