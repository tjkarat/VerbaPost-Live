"""
Admin Console — Phase 4 port of ui_admin.py.

GET  /admin                          dashboard: health, print queue, ghosts, credits, marketing
GET  /admin/letter/{kind}/{id}.pdf   print-ready letter PDF
GET  /admin/envelope/{kind}/{id}.pdf #10 window envelope PDF
POST /admin/queue/{kind}/{id}/sent   close an order
POST /admin/credits                  manual credit grant ("Central Bank")
POST /admin/marketing/letter.pdf     ad-hoc marketing letter PDF
POST /admin/marketing/envelope.pdf   ad-hoc marketing envelope PDF
GET  /admin/orphan-audio             authenticated Twilio audio proxy for ghost scans

Access: session role == "admin" (granted at login when email == ADMIN_EMAIL).
"""

import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import text

import ai_engine
import audit_engine
import database
import envelope_format
import invitation_format
import letter_format
import mailer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin")


def _require_admin(request: Request):
    return request.session.get("role") == "admin"


def _deny():
    return RedirectResponse("/login", status_code=302)


def _pdf(content, filename, download=0):
    """Serve a PDF inline by default so the admin can look at it and print
    straight from the browser's viewer; ?download=1 forces a save. Fulfillment
    is a visual check before it is a file — you want to see the envelope before
    you feed a real one through the printer."""
    disp = "attachment" if download else "inline"
    return Response(content=bytes(content), media_type="application/pdf",
                    headers={"Content-Disposition": f'{disp}; filename="{filename}"'})


# ---------- data helpers (ported from ui_admin) ----------

QUEUE_SQL = text("""
    SELECT p.id, p.advisor_email, p.content, p.status, p.heir_name, p.created_at,
           p.strategic_prompt, c.name AS parent_name, c.email AS heir_email,
           COALESCE(aup.advisor_firm, a.firm_name, 'VerbaPost') AS firm_name,
           up.address_line1, up.address_city, up.address_state, up.address_zip,
           up.full_name AS heir_full_name
    FROM projects p
    JOIN clients c ON p.client_id = c.id
    LEFT JOIN advisors a ON p.advisor_email = a.email
    LEFT JOIN user_profiles aup ON p.advisor_email = aup.email
    LEFT JOIN user_profiles up ON c.email = up.email
    WHERE p.status = 'Approved'
    ORDER BY p.created_at DESC
""")


def load_queue():
    items = []
    try:
        with database.get_db_session() as session:
            store = session.execute(text(
                "SELECT id, user_email, content, status FROM letter_drafts "
                "WHERE status IN ('Pending Approval', 'Approved')")).fetchall()
            for r in store:
                items.append({"kind": "store", "id": r.id, "who": r.user_email,
                              "content": r.content or "", "meta": {}})
            for r in session.execute(QUEUE_SQL).fetchall():
                heir_email = (r.heir_email or "").strip().lower()
                items.append({
                    "kind": "heirloom", "id": r.id,
                    "who": f"{r.heir_name or r.heir_full_name or 'Family'} (via {r.advisor_email})",
                    "content": r.content or "",
                    "meta": {
                        "firm_name": r.firm_name, "storyteller": r.parent_name,
                        "heir_name": r.heir_name or r.heir_full_name,
                        "heir_email": heir_email, "prompt": r.strategic_prompt,
                        "date": r.created_at.strftime("%B %d, %Y") if r.created_at else "Undated",
                        "address": {"line1": r.address_line1, "city": r.address_city,
                                    "state": r.address_state, "zip": r.address_zip},
                        # extra copies: the family's saved recipients (≤4)
                        "recipients": database.get_recipients(heir_email) if heir_email else [],
                    }})
    except Exception as e:
        logger.error(f"Queue load error: {e}")
    # Prospect acquisition letters (advisor-branded gift letters). Same manual
    # linen workflow; the envelope carries the ADVISOR's name and return address.
    try:
        pages = {}
        for r in database.list_prospect_letters(statuses=["Approved"]):
            adv = r.get("advisor_email") or ""
            if adv not in pages:
                pages[adv] = database.get_advisor_page_by_email(adv) or {}
            page = pages[adv]
            created = r.get("created_at")
            items.append({
                "kind": "prospect", "id": r.get("id"),
                "who": f"{r.get('prospect_name')} -> {r.get('recipient_name')} (gift from {page.get('display_name') or adv})",
                "content": r.get("letter_text") or r.get("transcript_raw") or "",
                "meta": {
                    "firm_name": page.get("firm_name") or "",
                    "advisor_name": page.get("display_name") or adv,
                    "advisor_email": adv,
                    "storyteller": r.get("prospect_name"),
                    "heir_name": r.get("recipient_name"),
                    "prompt": page.get("prompt") or "",
                    "date": created.strftime("%B %d, %Y") if hasattr(created, "strftime") else "Undated",
                    "address": {"line1": r.get("recipient_line1"), "city": r.get("recipient_city"),
                                "state": r.get("recipient_state"), "zip": r.get("recipient_zip")},
                    "return": {"line1": page.get("return_line1") or "", "city": page.get("return_city") or "",
                               "state": page.get("return_state") or "", "zip": page.get("return_zip") or ""},
                    "recipients": [],
                }})
    except Exception as e:
        logger.error(f"Prospect queue load error: {e}")
    return items


def _queue_item(kind: str, item_id: int):
    for it in load_queue():
        if it["kind"] == kind and str(it["id"]) == str(item_id):
            return it
    return None


def health_report():
    checks = []
    try:
        with database.get_db_session() as s:
            s.execute(text("SELECT 1"))
        checks.append(("ok", "Database (Supabase)", "Connected"))
    except Exception as e:
        checks.append(("fail", "Database", str(e)[:80]))
    for label, env in [("OpenAI", "OPENAI_API_KEY"), ("Twilio", "TWILIO_ACCOUNT_SID"),
                       ("Stripe", "STRIPE_SECRET_KEY"), ("Stripe webhook", "STRIPE_WEBHOOK_SECRET"),
                       ("Resend", "RESEND_API_KEY"), ("Email sender", "EMAIL_SENDER")]:
        checks.append(("ok", label, "Configured") if os.environ.get(env)
                      else ("warn", label, f"{env} missing"))
    return checks


def orphaned_calls():
    """Twilio recordings with no matching draft/project — nothing gets lost."""
    calls = ai_engine.get_all_twilio_recordings(limit=50)
    if not calls:
        return []
    known = set()
    try:
        with database.get_db_session() as session:
            # prospect_letters too: without it every acquisition-path call
            # looks orphaned, even one that produced a letter perfectly.
            for tbl in ("letter_drafts", "projects", "prospect_letters"):
                for row in session.execute(text(
                        f"SELECT call_sid FROM {tbl} WHERE call_sid IS NOT NULL")).fetchall():
                    known.add(row[0])
    except Exception as e:
        logger.error(f"Orphan scan DB error: {e}")
        return []
    return [c for c in calls if c["sid"] not in known]


# ---------- routes ----------

@router.get("", response_class=HTMLResponse)
def dashboard(request: Request):
    if not _require_admin(request):
        return _deny()
    from app.main import templates
    ghosts = orphaned_calls() if request.query_params.get("scan") else None
    return templates.TemplateResponse(request, "admin.html", {
        "health": health_report(),
        "queue": load_queue(),
        "ghosts": ghosts,
        "notice": request.query_params.get("notice"),
    })


@router.get("/letter/{kind}/{item_id}.pdf")
def letter_pdf(request: Request, kind: str, item_id: int, download: int = 0):
    if not _require_admin(request):
        return _deny()
    item = _queue_item(kind, item_id)
    if not item:
        return Response(status_code=404)
    meta = item["meta"]
    if kind == "prospect":
        who = meta.get("advisor_name") or "Your Advisor"
        if meta.get("firm_name"):
            who = f"{who}, {meta['firm_name']}"
        pdf = letter_format.create_pdf(
            body_text=item["content"], to_addr={},
            from_addr={"name": meta.get("storyteller", "A Friend")},
            advisor_firm=meta.get("firm_name") or who,
            audio_url=f"p{item['id']}",          # QR -> /play/p{id} (always released)
            is_marketing=False, question_text=meta.get("prompt"),
            compliments_of=who, recipient_name=meta.get("heir_name"))
        return _pdf(pdf, f"prospect_letter_{item_id}.pdf", download)
    pdf = letter_format.create_pdf(
        body_text=item["content"], to_addr={},
        from_addr={"name": meta.get("storyteller", "The Family")},
        advisor_firm=meta.get("firm_name", "VerbaPost"),
        audio_url=str(item["id"]) if kind == "heirloom" else None,
        is_marketing=False, question_text=meta.get("prompt"))
    return _pdf(pdf, f"letter_{item_id}.pdf", download)


@router.get("/envelope/{kind}/{item_id}.pdf")
def envelope_pdf(request: Request, kind: str, item_id: int, recipient: int = -1,
                 download: int = 0):
    """recipient=-1 -> the heir; 0..n -> index into the extra recipients."""
    if not _require_admin(request):
        return _deny()
    item = _queue_item(kind, item_id)
    if not item:
        return Response(status_code=404)
    meta = item["meta"]
    if kind == "prospect":
        # Advisor's name (and firm) as the return address — the gift is theirs.
        ret = meta.get("return", {})
        from_name = meta.get("advisor_name") or "Your Advisor"
        if meta.get("firm_name"):
            from_name = f"{from_name}\n{meta['firm_name']}"
        from_obj = {"name": from_name, "address_line1": ret.get("line1", ""),
                    "city": ret.get("city", ""), "state": ret.get("state", ""),
                    "zip_code": ret.get("zip", "")}
        a = meta.get("address", {})
        to_obj = {"name": meta.get("heir_name"), "address_line1": a.get("line1") or "",
                  "city": a.get("city") or "", "state": a.get("state") or "",
                  "zip_code": a.get("zip") or ""}
    elif kind == "heirloom":
        adv = database.get_user_profile(item["who"].split("via ")[-1].rstrip(")"))
        from_obj = {"name": meta.get("firm_name") or "VerbaPost",
                    "address_line1": (adv or {}).get("address_line1", ""),
                    "city": (adv or {}).get("address_city", ""),
                    "state": (adv or {}).get("address_state", ""),
                    "zip_code": (adv or {}).get("address_zip", "")}
        if recipient >= 0 and recipient < len(meta.get("recipients", [])):
            r = meta["recipients"][recipient]
            to_obj = {"name": r.get("name"), "address_line1": r.get("street", ""),
                      "city": r.get("city", ""), "state": r.get("state", ""),
                      "zip_code": r.get("zip_code", "")}
        else:
            a = meta.get("address", {})
            to_obj = {"name": meta.get("heir_name"), "address_line1": a.get("line1") or "",
                      "city": a.get("city") or "", "state": a.get("state") or "",
                      "zip_code": a.get("zip") or ""}
    else:
        from_obj = {"name": "VerbaPost Fulfillment", "address_line1": "",
                    "city": "Nashville", "state": "TN", "zip_code": "37203"}
        prof = database.get_user_profile(item["who"])
        to_obj = {"name": (prof or {}).get("full_name") or item["who"],
                  "address_line1": (prof or {}).get("address_line1", ""),
                  "city": (prof or {}).get("address_city", ""),
                  "state": (prof or {}).get("address_state", ""),
                  "zip_code": (prof or {}).get("address_zip", "")}
    env = envelope_format.create_envelope(to_obj, from_obj)
    if not env:
        return Response(status_code=500)
    return _pdf(env, f"envelope_{item_id}_{recipient}.pdf", download)


@router.post("/queue/{kind}/{item_id}/sent")
def mark_sent(request: Request, kind: str, item_id: int):
    if not _require_admin(request):
        return _deny()
    if kind == "prospect":
        from datetime import datetime as _dt
        database.update_prospect_letter(item_id, status="Sent", sent_at=_dt.utcnow())
        audit_engine.log_event(request.session.get("email", "admin"), "Order Marked Sent",
                               metadata={"kind": kind, "id": item_id})
        return RedirectResponse("/admin?notice=Order+closed", status_code=303)
    table = "projects" if kind == "heirloom" else "letter_drafts"
    try:
        with database.get_db_session() as session:
            session.execute(text(f"UPDATE {table} SET status = 'Sent' WHERE id = :id"),  # noqa: S608 — table from fixed map
                            {"id": item_id})
        audit_engine.log_event(request.session.get("email", "admin"), "Order Marked Sent",
                               metadata={"kind": kind, "id": item_id})
    except Exception as e:
        logger.error(f"Mark sent failed: {e}")
    return RedirectResponse("/admin?notice=Order+closed", status_code=303)


@router.post("/credits")
def grant_credits(request: Request, email: str = Form(...), amount: int = Form(...)):
    if not _require_admin(request):
        return _deny()
    email = email.strip().lower()
    granted = False
    try:
        with database.get_db_session() as session:
            for tbl in ("user_profiles", "advisors"):
                row = session.execute(text(f"SELECT credits FROM {tbl} WHERE email = :e"),
                                      {"e": email}).fetchone()
                if row is not None:
                    session.execute(text(f"UPDATE {tbl} SET credits = :v WHERE email = :e"),
                                    {"v": (row[0] or 0) + amount, "e": email})
                    granted = True
    except Exception as e:
        logger.error(f"Credit grant failed: {e}")
    if granted:
        audit_engine.log_event(request.session.get("email", "admin"), "Manual Credit Grant",
                               metadata={"target": email, "amount": amount})
        return RedirectResponse(f"/admin?notice=Granted+{amount}+to+{email}", status_code=303)
    return RedirectResponse("/admin?notice=User+not+found", status_code=303)


@router.post("/marketing/letter.pdf")
def marketing_letter(request: Request, name: str = Form(""), address: str = Form(""),
                     return_address: str = Form(""), body: str = Form("")):
    if not _require_admin(request):
        return _deny()
    pdf = letter_format.create_pdf(
        body_text=body, to_addr=_parse_addr(f"{name}\n{address}"),
        from_addr=_parse_addr(return_address),
        advisor_firm="VerbaPost Marketing", is_marketing=True)
    return Response(content=bytes(pdf), media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="marketing_letter.pdf"'})


@router.post("/marketing/envelope.pdf")
def marketing_envelope(request: Request, name: str = Form(""), address: str = Form(""),
                       return_address: str = Form("")):
    if not _require_admin(request):
        return _deny()
    env = envelope_format.create_envelope(
        _parse_addr(f"{name}\n{address}"), _parse_addr(return_address))
    return Response(content=bytes(env or b""), media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="marketing_envelope.pdf"'})


@router.post("/prospect/grant")
def grant_prospect_letters(request: Request, email: str = Form(...), amount: int = Form(...),
                           note: str = Form("")):
    """Central Bank for the acquisition path: letter credits for deals closed
    in person / invoiced by hand. Writes a 'grant' ledger row (not a purchase,
    so it does NOT flip the advisor to repeat pricing)."""
    if not _require_admin(request):
        return _deny()
    email = email.strip().lower()
    if amount == 0 or "@" not in email:
        return RedirectResponse("/admin?notice=Invalid+grant", status_code=303)
    ok = database.add_prospect_credits(email, amount, "grant",
                                       f"admin:{request.session.get('email', 'admin')} {note.strip()[:80]}")
    if ok:
        audit_engine.log_event(request.session.get("email", "admin"), "Prospect Letters Granted",
                               metadata={"target": email, "amount": amount, "note": note[:80]})
        return RedirectResponse(f"/admin?notice=Granted+{amount}+prospect+letters+to+{email}", status_code=303)
    return RedirectResponse("/admin?notice=Grant+failed", status_code=303)


@router.get("/prospect/export.csv")
def prospect_export_all(request: Request):
    """Every advisor's send log — the advertising-records export for the house."""
    if not _require_admin(request):
        return _deny()
    from app.advisor import prospect_csv
    return prospect_csv(database.list_prospect_letters(), filename="verbapost_prospect_send_log.csv")


@router.api_route("/pcm/probe.pdf", methods=["GET", "HEAD"])
def pcm_probe_pdf():
    """The artwork the probe order below points PCM at. Unauthenticated on
    purpose, same reasoning as /a/{slug}/i/{token}/pdf: PCM's mail API fetches
    artwork by URL, it has no way to send our admin session cookie, and this
    is a fixed, harmless test letter — never real prospect data."""
    pdf = invitation_format.create_invitation_pdf(
        first_name="Probe", personal_url="https://app.verbapost.com/a/probe/i/PROBE",
        advisor_name="VerbaPost Probe", firm_name="VerbaPost",
        compact=(mailer.get_mail_provider() == "pcm"))
    if not pdf:
        return Response(status_code=500)
    return Response(content=pdf, media_type="application/pdf")


@router.get("/pcm/probe")
def pcm_probe(request: Request):
    """Places ONE real PCM letter order addressed to VerbaPost itself, so a
    credentials/connectivity problem surfaces before a real advisor mailing
    does. The request schema is confirmed from PCM's own OpenAPI spec (see
    mailer.py); this is not schema discovery, it is a live smoke test — so
    run it against a Sandbox apiKey/apiSecret pair first, never straight
    against Production."""
    if not _require_admin(request):
        return _deny()
    base_url = os.environ.get("BASE_URL", "https://app.verbapost.com").rstrip("/")
    result = mailer.pcm_probe(
        f"{base_url}/admin/pcm/probe.pdf",
        {"name": "Tarak Robbana", "line1": "1008 Brandon Court", "city": "Mt. Juliet",
         "state": "TN", "zip": "37122"},
        {"name": "VerbaPost", "company": "VerbaPost Inc.", "line1": "1008 Brandon Court",
         "city": "Mt. Juliet", "state": "TN", "zip": "37122"})
    audit_engine.log_event(request.session.get("email", "admin"), "PCM Probe",
                           metadata={"status": result.get("status"), "ok": result.get("ok")})
    import json as _json
    return Response(content=_json.dumps(result, indent=2), media_type="application/json")


@router.get("/orphan-audio")
def orphan_audio(request: Request, uri: str = ""):
    if not _require_admin(request):
        return _deny()
    if not uri.startswith("/"):
        return Response(status_code=400)
    audio = ai_engine.fetch_recording_audio(uri)
    if not audio:
        return Response(status_code=502)
    return Response(content=audio, media_type="audio/mpeg")


def _parse_addr(raw: str):
    """Text block -> envelope dict (ported from ui_admin.parse_address_text)."""
    parts = [p.strip() for p in (raw or "").split("\n") if p.strip()]
    data = {"name": "", "address_line1": "", "city": "", "state": "", "zip_code": ""}
    if parts:
        data["name"] = parts[0]
    if len(parts) >= 2:
        data["address_line1"] = parts[1]
    if len(parts) >= 3 and "," in parts[2]:
        city, rest = parts[2].split(",", 1)
        data["city"] = city.strip()
        bits = rest.strip().rsplit(" ", 1)
        data["state"] = bits[0] if bits else rest.strip()
        data["zip_code"] = bits[1] if len(bits) > 1 else ""
    elif len(parts) >= 3:
        data["city"] = parts[2]
    return data


# ---------- retention ----------
#
# The Terms promise the audio goes after a fixed window. Nothing enforced that
# until this page existed. It is deliberately manual and dry-run-first: the
# deletion reaches Twilio and is irreversible, so a human sees the list before
# anything goes. The printed letter and the transcript are never touched.

@router.get("/retention", response_class=HTMLResponse)
def retention_review(request: Request):
    if not _require_admin(request):
        return _deny()
    import retention
    from app.player import RETENTION_DAYS
    rows, _ = retention.purge_expired(dry_run=True)
    body = "".join(
        f"<tr><td>{r['id']}</td><td>{(r['storyteller'] or '')}</td>"
        f"<td>{r['created_at']:%b %d, %Y}</td><td>{r['age_days']}</td></tr>"
        for r in rows)
    table = (f"<table border=1 cellpadding=6 cellspacing=0><tr><th>Letter</th>"
             f"<th>Storyteller</th><th>Recorded</th><th>Days old</th></tr>{body}</table>"
             if rows else "<p>Nothing is past the window. No audio to purge.</p>")
    confirm = ("""
      <form method="post" action="/admin/retention/purge"
            onsubmit="return confirm('Delete this audio at Twilio? This cannot be undone.')">
        <p>Type <code>purge</code> to confirm, then press the button.</p>
        <input name="confirm" autocomplete="off" required>
        <button type="submit">Purge audio</button>
      </form>""" if rows else "")
    return HTMLResponse(
        f"""<!doctype html><meta charset="utf-8"><title>Retention</title>
        <body style="font-family:Georgia,serif;max-width:760px;margin:40px auto;padding:0 20px">
        <h1>Audio retention</h1>
        <p>Recordings are kept for <strong>{RETENTION_DAYS} days</strong> from the
        recording date. Below is what is past that window right now. Purging
        clears our pointer and deletes the media at Twilio. The printed letter
        and the transcript stay.</p>
        {table}{confirm}
        <p><a href="/admin">&larr; Back to admin</a></p></body>""")


@router.post("/retention/purge")
def retention_purge(request: Request, confirm: str = Form("")):
    if not _require_admin(request):
        return _deny()
    if confirm.strip().lower() != "purge":
        return RedirectResponse("/admin/retention?notice=Not+confirmed", status_code=303)
    import retention
    results, errors = retention.purge_expired(dry_run=False)
    audit_engine.log_event(request.session.get("email", "admin"), "Audio Retention Purge",
                           metadata={"purged": len(results), "errors": len(errors)})
    return RedirectResponse(
        f"/admin?notice=Purged+{len(results)}+recording(s),+{len(errors)}+error(s)",
        status_code=303)
