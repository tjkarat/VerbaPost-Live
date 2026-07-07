"""
Public QR-code audio player — Phase 1.

GET /play/{audio_id}            the player page (no login; QR codes on mailed letters)
GET /play/{audio_id}/audio.mp3  server-side audio proxy (keeps Twilio creds off the browser)

Port of ui_heirloom.render_public_player.
"""

import logging
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

import ai_engine
import database

logger = logging.getLogger(__name__)
router = APIRouter()

DEMO = {
    "url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
    "title": "Barnaby Jones - Childhood Memories",
    "date": "January 16, 2026",
    "storyteller": "Barnaby Jones",
}


def _load_story(audio_id: str):
    if audio_id in ("demo", "sample"):
        return dict(DEMO)
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
        },
    )


@router.get("/play/{audio_id}/audio.mp3")
def public_player_audio(audio_id: str):
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

    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={"Cache-Control": "private, max-age=3600"},
    )
