"""
Retention — enforce the window the Terms actually promise.

Until now the window existed only as text: nothing deleted anything. Publishing
a retention policy you do not follow is worse than either keeping the audio or
deleting it, so this is the job that makes the words true.

For recordings past the window it:
  * clears the row's pointer to the audio, so the player stops serving it
  * optionally deletes the recording at Twilio, which is where the media
    actually lives — clearing our pointer alone destroys nothing

What it deliberately does NOT do:
  * touch the letter text or the transcript. The printed letter is the
    permanent artifact; only the audio expires.
  * touch the public sample (player.SAMPLE_LETTER_ID), which the marketing
    site and the mailer both point at.
  * run on a schedule. Nothing calls this automatically. It is invoked from
    /admin/retention and defaults to a dry run, because the deletion is
    irreversible and whoever presses the button should see the list first.
"""

import logging
from datetime import datetime, timedelta

import ai_engine
import database

logger = logging.getLogger(__name__)


def _retention_days():
    from app.player import RETENTION_DAYS
    return RETENTION_DAYS


def _protected_ids():
    """Letters the purge must never touch."""
    from app.player import SAMPLE_LETTER_ID
    return {int(SAMPLE_LETTER_ID)}


def find_expired(now=None):
    """Rows whose audio is past the window. Read-only."""
    now = now or datetime.utcnow()
    cutoff = now - timedelta(days=_retention_days())
    protected = _protected_ids()
    out = []
    try:
        for row in database.list_prospect_letters(statuses=["Approved", "Sent"]):
            if int(row.get("id")) in protected:
                continue
            if not row.get("audio_url"):
                continue
            created = row.get("created_at")
            if not hasattr(created, "date") or created > cutoff:
                continue
            out.append({
                "id": row.get("id"),
                "storyteller": row.get("prospect_name"),
                "created_at": created,
                "age_days": (now - created).days,
                "audio_url": row.get("audio_url"),
            })
    except Exception:
        logger.exception("Retention scan failed")
    return out


def purge_expired(dry_run=True, delete_at_twilio=True, now=None):
    """Clear expired audio. Returns (results, errors).

    dry_run=True (the default) reports what would go without touching
    anything. Nothing here deletes a letter, a transcript or a row.
    """
    expired = find_expired(now=now)
    results, errors = [], []

    for item in expired:
        letter_id = item["id"]
        if dry_run:
            results.append({**item, "action": "would purge"})
            continue
        try:
            if delete_at_twilio and "api.twilio.com" in (item["audio_url"] or ""):
                ok = ai_engine.delete_recording(item["audio_url"])
                if not ok:
                    errors.append({"id": letter_id, "error": "twilio delete failed"})
            database.update_prospect_letter(letter_id, audio_url=None)
            database.log_event("system", "Audio Purged",
                               {"letter_id": letter_id, "age_days": item["age_days"],
                                "retention_days": _retention_days()})
            results.append({**item, "action": "purged"})
        except Exception as e:
            logger.exception(f"Purge failed for letter {letter_id}")
            errors.append({"id": letter_id, "error": str(e)[:200]})

    return results, errors
