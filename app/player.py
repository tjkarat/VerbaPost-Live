"""
Public QR-code audio player — Phase 1.

GET /play/{audio_id}            the player page (no login; QR codes on mailed letters)
GET /play/{audio_id}/audio.mp3  server-side audio proxy (keeps Twilio creds off the browser)

Port of ui_heirloom.render_public_player.
"""

import logging
import sys
from pathlib import Path
from datetime import timedelta
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

import ai_engine
import database

logger = logging.getLogger(__name__)
router = APIRouter()

# How long a recording stays downloadable. Must match the Terms — see
# app/templates/legal.html and ui_legal.py.
RETENTION_DAYS = 60

# The story used as the public sample: on the advisor landing page, in the
# mailer, and anywhere marketing needs a real letter. Pointing /play/sample at
# a real letter means the sample can never drift from the product; the purge
# job skips this one so it does not go quiet.
SAMPLE_LETTER_ID = 3


def _load_story(audio_id: str):
    if audio_id in ("demo", "sample"):
        return _load_story(f"p{SAMPLE_LETTER_ID}")
    # Prospect letters carry a "p" prefix on the QR code (/play/p123).
    # Their audio is always playable — the recipient hearing the prospect's
    # voice IS the gift; there is no advisor release gate on this path.
    if audio_id.startswith("p") and audio_id[1:].isdigit():
        letter = database.get_prospect_letter(audio_id[1:])
        if letter and letter.get("audio_url") and letter.get("status") in ("Approved", "Sent"):
            created = letter.get("created_at")
            # Who gifted it. A letter arrives as a gift from a named advisor;
            # landing on an unbranded page loses that, and leaves the visitor
            # with nowhere to go but a login screen they have no account for.
            page = database.get_advisor_page_by_email(letter.get("advisor_email") or "") or {}
            # The public sample is exempt from the purge, so it must not
            # advertise an expiry date it will never reach.
            permanent = int(letter.get("id") or 0) == int(SAMPLE_LETTER_ID)
            expires = None
            if hasattr(created, "strftime") and not permanent:
                expires = (created + timedelta(days=RETENTION_DAYS)).strftime("%B %d, %Y")
            return {
                "permanent": permanent,
                "expires_on": expires,
                "id": audio_id,
                "url": letter["audio_url"],
                "title": f"A story from {letter.get('prospect_name') or 'a friend'}",
                "date": created.strftime("%B %d, %Y") if hasattr(created, "strftime") else "",
                "storyteller": letter.get("prospect_name") or "Storyteller",
                "released": True,
                "advisor_name": page.get("display_name") or "",
                "firm_name": page.get("firm_name") or "",
                "advisor_slug": page.get("slug") or "",
            }
        return None
    data = database.get_public_draft(audio_id)
    if data and data.get("url"):
        return data
    return None


def _is_twilio_url(url: str) -> bool:
    return "api.twilio.com" in (url or "")


@router.get("/play/{audio_id}", response_class=HTMLResponse)
def public_player(request: Request, audio_id: str):
    from app.main import templates  # avoid circular import at module load

    story = _load_story(audio_id)
    if not story:
        return templates.TemplateResponse(
            request, "play.html",
            {"found": False, "locked": False, "title": "Story not found"},
            status_code=404,
        )

    # Advisor-release gate: the heir's path to the recording runs through
    # the advisor. (Demo and legacy drafts carry released=True.)
    if not story.get("released", True):
        return templates.TemplateResponse(
            request, "play.html",
            {"found": True, "locked": True,
             "title": story.get("title", "Private Recording"),
             "storyteller": story.get("storyteller", "Family Member"),
             "date": story.get("date", "")},
        )

    # Twilio URLs need auth — stream via our proxy. Public URLs go direct.
    if _is_twilio_url(story["url"]):
        audio_src = f"/play/{audio_id}/audio.mp3"
    else:
        audio_src = story["url"]

    return templates.TemplateResponse(
        request, "play.html",
        {
            "found": True,
            "locked": False,
            "title": story.get("title", "Private Recording"),
            "storyteller": story.get("storyteller", "Family Member"),
            "date": story.get("date", "Unknown Date"),
            "audio_src": audio_src,
            "advisor_name": story.get("advisor_name", ""),
            "firm_name": story.get("firm_name", ""),
            "advisor_slug": story.get("advisor_slug", ""),
            "expires_on": story.get("expires_on"),
            "retention_days": None if story.get("permanent") else RETENTION_DAYS,
            "download_src": f"/play/{audio_id}/audio.mp3?download=1",
        },
    )


@router.get("/play/{audio_id}/audio.mp3")
def public_player_audio(audio_id: str, download: int = 0):
    """Authenticated server-side fetch of Twilio-hosted audio."""
    story = _load_story(audio_id)
    if not story:
        return Response(status_code=404)
    # Same gate as the page — otherwise the direct mp3 URL bypasses the lock.
    if not story.get("released", True):
        return Response(status_code=403)

    url = story["url"]
    if not _is_twilio_url(url):
        return RedirectResponse(url)

    partial_uri = urlparse(url).path  # fetch_recording_audio expects the path part
    audio_bytes = ai_engine.fetch_recording_audio(partial_uri)
    if not audio_bytes:
        return Response(status_code=502)

    headers = {"Cache-Control": "private, max-age=3600"}
    if download:
        # Content-Disposition rather than the <a download> attribute alone:
        # mobile Safari ignores the attribute and plays the file instead.
        teller = (story.get("storyteller") or "story").replace('"', "").replace(" ", "_")
        headers["Content-Disposition"] = f'attachment; filename="{teller}_VerbaPost.mp3"'
    return Response(content=audio_bytes, media_type="audio/mpeg", headers=headers)
