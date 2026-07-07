"""
Family (Heirloom) dashboard + Heir archive — Phase 3 port of ui_heirloom.py / ui_archive.py.

GET  /heirloom                      family dashboard (interview station + story vault)
POST /heirloom/prep-email           notify the storyteller before the call
POST /heirloom/call                 trigger the AI biographer call
POST /heirloom/address              save shipping address
POST /heirloom/draft/{id}/save      save transcript edits
POST /heirloom/draft/{id}/polish    AI grammar/filler cleanup
POST /heirloom/draft/{id}/mail      queue letter for (manual linen) printing
GET  /archive/{pid}                 heir vault — QR landing from the physical letter
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

import ai_engine
import audit_engine
import database
import email_engine

logger = logging.getLogger(__name__)
router = APIRouter()

CREDIT_COST = 1

# Post/Redirect/Get message codes (avoids echoing raw user input)
MESSAGES = {
    "prep_sent": ("notice", "Preparation email sent to the storyteller."),
    "prep_fail": ("error", "Could not send the preparation email."),
    "bad_email": ("error", "Please enter a valid email address."),
    "bad_phone": ("error", "Please enter a valid 10-digit phone number."),
    "call_started": ("notice", "Calling now — the biographer is dialing. The story will appear below when the call ends."),
    "call_fail": ("error", "The call could not be started. Please check the number and try again."),
    "saved": ("notice", "Changes saved."),
    "polished": ("notice", "Story polished."),
    "addr_saved": ("notice", "Shipping address saved."),
    "queued": ("notice", "Added to the print queue. Your letter will be prepared on linen stock and mailed — you'll receive tracking by email."),
    "no_credits": ("error", "No story credits remaining for this archive. Your advisor can commission an additional story for your family."),
    "queue_fail": ("error", "Could not queue the letter. Please try again."),
    "denied": ("error", "That story does not belong to this account."),
    "details_saved": ("notice", "Interview details saved. You can now send the prep email and start the call."),
    "no_details": ("error", "Save the interview details (phone and question) first."),
    "recipient_added": ("notice", "Recipient added — they'll receive their own copy of each mailed story."),
    "recipient_fail": ("error", "Could not add that recipient. Check the fields, or you may have reached the limit of 4."),
}


def _owns_draft(email: str, draft_id) -> bool:
    """Server-side ownership check — draft IDs arrive from the URL and must
    never be trusted. A user may only touch drafts in their own vault."""
    try:
        return any(str(d.get("id")) == str(draft_id)
                   for d in database.get_user_drafts(email))
    except Exception:
        return False


def _profile(request: Request):
    email = request.session.get("email")
    if not email:
        return None
    return email, (database.get_user_profile(email) or {})


def _days_left(created):
    if isinstance(created, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
            try:
                created = datetime.strptime(created[:26], fmt)
                break
            except ValueError:
                continue
    if not isinstance(created, datetime):
        return 30
    return 30 - (datetime.now() - created).days


@router.get("/heirloom", response_class=HTMLResponse)
def dashboard(request: Request):
    from app.main import templates
    auth = _profile(request)
    if not auth:
        return RedirectResponse("/login", status_code=302)
    email, profile = auth

    is_sponsored = (profile.get("role") in ("heir", "heirloom")
                    or profile.get("created_by") is not None)

    kind, text = (None, None)
    code = request.query_params.get("m")
    if code in MESSAGES:
        kind, text = MESSAGES[code]

    drafts = []
    if is_sponsored:
        for d in database.get_user_drafts(email):
            d = dict(d)
            d["days_left"] = _days_left(d.get("created_at"))
            audio = d.get("tracking_number") or ""
            if "api.twilio.com" in str(audio):
                d["audio_src"] = f"/play/{d.get('id')}/audio.mp3"
            elif "http" in str(audio):
                d["audio_src"] = audio
            else:
                d["audio_src"] = None
            drafts.append(d)

    has_address = all(profile.get(k) for k in
                      ("address_line1", "address_city", "address_state", "address_zip"))

    # Saved interview details (session-first, profile fallback for phone)
    iv_phone = request.session.get("iv_phone") or profile.get("parent_phone") or ""
    iv_email = request.session.get("iv_email") or ""
    iv_question = request.session.get("iv_question") or ""
    details_saved = bool(iv_phone and iv_question)

    recipients = database.get_recipients(email) if is_sponsored else []

    return templates.TemplateResponse(request, "heirloom.html", {
        "iv_phone": iv_phone, "iv_email": iv_email, "iv_question": iv_question,
        "details_saved": details_saved,
        "recipients": recipients,
        "max_recipients": database.MAX_EXTRA_RECIPIENTS,
        "profile": profile,
        "is_sponsored": is_sponsored,
        "advisor_firm": profile.get("advisor_firm") or "VerbaPost",
        "credits": profile.get("credits", 0) or 0,
        "drafts": drafts,
        "has_address": has_address,
        "msg_kind": kind, "msg_text": text,
    })


@router.post("/heirloom/interview/save")
def save_interview_details(request: Request, target_phone: str = Form(""),
                           target_email: str = Form(""), question: str = Form("")):
    """Save-first flow: details are stored (phone also persisted to the
    profile), and only then do the prep-email / call buttons unlock."""
    auth = _profile(request)
    if not auth:
        return RedirectResponse("/login", status_code=302)
    email, _ = auth
    clean_phone = "".join(filter(str.isdigit, target_phone))
    if len(clean_phone) < 10:
        return RedirectResponse("/heirloom?m=bad_phone", status_code=303)
    if target_email and "@" not in target_email:
        return RedirectResponse("/heirloom?m=bad_email", status_code=303)
    request.session["iv_phone"] = clean_phone
    request.session["iv_email"] = target_email.strip()
    request.session["iv_question"] = question.strip() or \
        "Please share a favorite memory from your childhood."
    try:
        from database import supabase
        if supabase:
            supabase.table("user_profiles").update(
                {"parent_phone": clean_phone}).eq("email", email).execute()
    except Exception as e:
        logger.error(f"Phone persist failed for {email}: {e}")
    return RedirectResponse("/heirloom?m=details_saved", status_code=303)


@router.post("/heirloom/prep-email")
def prep_email(request: Request, target_email: str = Form(""), question: str = Form("")):
    auth = _profile(request)
    if not auth:
        return RedirectResponse("/login", status_code=302)
    email, profile = auth
    # Posted values win (API/backward compat); saved details otherwise.
    target_email = (target_email or request.session.get("iv_email") or "").strip()
    question = (question or request.session.get("iv_question") or "").strip()
    if "@" not in target_email:
        return RedirectResponse("/heirloom?m=bad_email", status_code=303)
    if not question:
        return RedirectResponse("/heirloom?m=no_details", status_code=303)
    sent = email_engine.send_interview_prep_email(
        target_email, profile.get("advisor_firm") or "Your Advisor", question)
    if sent:
        audit_engine.log_event(email, "Prep Email Sent", metadata={"target": target_email})
        return RedirectResponse("/heirloom?m=prep_sent", status_code=303)
    return RedirectResponse("/heirloom?m=prep_fail", status_code=303)


@router.post("/heirloom/call")
def start_call(request: Request, target_phone: str = Form(""), question: str = Form("")):
    auth = _profile(request)
    if not auth:
        return RedirectResponse("/login", status_code=302)
    email, profile = auth

    # Posted values win (API/backward compat); saved details otherwise.
    target_phone = target_phone or request.session.get("iv_phone") or ""
    clean_phone = "".join(filter(str.isdigit, target_phone))
    if len(clean_phone) < 10:
        return RedirectResponse("/heirloom?m=bad_phone", status_code=303)
    q = (question or request.session.get("iv_question") or "").strip() \
        or "Please share a favorite memory from your childhood."

    sid, err = ai_engine.trigger_outbound_call(
        to_phone=clean_phone,
        advisor_name=profile.get("advisor_firm") or "Your Advisor",
        firm_name=profile.get("advisor_firm") or "VerbaPost",
        project_id=profile.get("id"),
        question_text=q)
    if not sid:
        logger.error(f"Call failed for {email}: {err}")
        return RedirectResponse("/heirloom?m=call_fail", status_code=303)

    database.create_draft(user_email=email, content="Waiting for recording...",
                          status="Pending", call_sid=sid, prompt=q)
    audit_engine.log_event(email, "Interview Started", metadata={"sid": sid})

    adv_email = profile.get("advisor_email") or profile.get("created_by")
    if adv_email:
        email_engine.send_advisor_heir_started_alert(
            advisor_email=adv_email,
            heir_name=profile.get("full_name") or "Family Member",
            client_name=profile.get("parent_name") or "Client")
    return RedirectResponse("/heirloom?m=call_started", status_code=303)


@router.post("/heirloom/address")
def save_address(request: Request, street: str = Form(...), city: str = Form(...),
                 state: str = Form(...), zip_code: str = Form(...)):
    auth = _profile(request)
    if not auth:
        return RedirectResponse("/login", status_code=302)
    email, _ = auth
    try:
        from database import supabase
        if supabase:
            supabase.table("user_profiles").update({
                "address_line1": street.strip(), "address_city": city.strip(),
                "address_state": state.strip(), "address_zip": zip_code.strip(),
            }).eq("email", email).execute()
    except Exception as e:
        logger.error(f"Address save failed for {email}: {e}")
    return RedirectResponse("/heirloom?m=addr_saved", status_code=303)


@router.post("/heirloom/recipients/add")
def add_recipient(request: Request, name: str = Form(...), street: str = Form(...),
                  city: str = Form(...), state: str = Form(...),
                  zip_code: str = Form(...)):
    email = request.session.get("email")
    if not email:
        return RedirectResponse("/login", status_code=302)
    ok, msg = database.add_recipient(email, name, street, city, state, zip_code)
    return RedirectResponse("/heirloom?m=" + ("recipient_added" if ok else "recipient_fail"),
                            status_code=303)


@router.post("/heirloom/recipients/{rid}/delete")
def remove_recipient(request: Request, rid: int):
    email = request.session.get("email")
    if not email:
        return RedirectResponse("/login", status_code=302)
    database.delete_recipient(rid, email)  # ownership enforced in the query
    return RedirectResponse("/heirloom", status_code=303)


@router.post("/heirloom/draft/{draft_id}/save")
def save_draft(request: Request, draft_id: int, content: str = Form(...)):
    email = request.session.get("email")
    if not email:
        return RedirectResponse("/login", status_code=302)
    if not _owns_draft(email, draft_id):
        return RedirectResponse("/heirloom?m=denied", status_code=303)
    database.update_draft(draft_id, content)
    return RedirectResponse("/heirloom?m=saved", status_code=303)


@router.post("/heirloom/draft/{draft_id}/polish")
def polish_draft(request: Request, draft_id: int, content: str = Form(...)):
    email = request.session.get("email")
    if not email:
        return RedirectResponse("/login", status_code=302)
    if not _owns_draft(email, draft_id):
        return RedirectResponse("/heirloom?m=denied", status_code=303)
    polished = ai_engine.refine_text(content)
    if polished:
        database.update_draft(draft_id, polished)
    return RedirectResponse("/heirloom?m=polished", status_code=303)


@router.post("/heirloom/draft/{draft_id}/mail")
def queue_letter(request: Request, draft_id: int, content: str = Form("")):
    auth = _profile(request)
    if not auth:
        return RedirectResponse("/login", status_code=302)
    email, profile = auth
    if not _owns_draft(email, draft_id):
        return RedirectResponse("/heirloom?m=denied", status_code=303)
    credits = profile.get("credits", 0) or 0
    if credits < CREDIT_COST:
        return RedirectResponse("/heirloom?m=no_credits", status_code=303)
    try:
        if content.strip():
            database.update_draft(draft_id, content)
        database.update_user_credits(email, credits - CREDIT_COST)
        database.update_project_details(draft_id, status="Approved")
        # Build the full mailing list: heir's own address + saved recipients
        mailing_list = [{
            "name": profile.get("full_name") or email,
            "street": profile.get("address_line1"), "city": profile.get("address_city"),
            "state": profile.get("address_state"), "zip_code": profile.get("address_zip"),
        }] + database.get_recipients(email)
        audit_engine.log_event(email, "Manual Print Queued",
                               metadata={"draft_id": draft_id, "letters": len(mailing_list)})
        email_engine.send_admin_print_ready_alert(
            user_email=email, draft_id=draft_id, content_preview=content[:500],
            mailing_list=mailing_list)
        return RedirectResponse("/heirloom?m=queued", status_code=303)
    except Exception as e:
        logger.error(f"Queue failed for draft {draft_id}: {e}")
        return RedirectResponse("/heirloom?m=queue_fail", status_code=303)


# ============================================================
# Heir vault — QR landing from the physical letter (public)
# ============================================================

@router.get("/archive/{pid}", response_class=HTMLResponse)
def heir_vault(request: Request, pid: str):
    from app.main import templates
    project = database.get_project_by_id(pid)
    if not project:
        return templates.TemplateResponse(
            request, "coming_soon.html",
            {"title": "Archive not found",
             "detail": "The link may be invalid — please re-scan the QR code on your letter."},
            status_code=404)

    heir_name = project.get("heir_name")
    if not heir_name or heir_name == "None":
        heir_name = "Family Member"

    audio_url = project.get("audio_ref") or project.get("tracking_number") or ""
    if "api.twilio.com" in str(audio_url):
        audio_src = f"/play/{project.get('id')}/audio.mp3"
    elif "http" in str(audio_url):
        audio_src = audio_url
    else:
        audio_src = None

    return templates.TemplateResponse(request, "archive.html", {
        "firm_name": project.get("firm_name") or "VerbaPost Wealth",
        "heir_name": heir_name,
        "parent_name": project.get("parent_name") or "Your Loved One",
        "released": bool(project.get("audio_released")),
        "audio_src": audio_src,
    })
