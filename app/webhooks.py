"""
Webhook endpoints — Phase 1.

/webhooks/stripe            Stripe checkout fulfillment (replaces redirect-only flow)
/webhooks/twilio/recording  Twilio recording-complete -> transcribe -> save draft
/webhooks/twilio/review     a take ended -> play it back, offer a redo
/webhooks/twilio/review/decide  keep this take, or record another

Both verify cryptographic signatures before trusting anything in the request.
Both hand real work to background tasks so the caller gets a fast 200
(Stripe and Twilio retry on slow/failed responses — we never want that
to double-process).
"""

import logging
import os
import time
import sys
from pathlib import Path

# Engines live at repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests
import stripe as stripe_lib
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import PlainTextResponse
from twilio.request_validator import RequestValidator
from urllib.parse import quote, unquote

import ai_engine
import database
import payment_engine
import secrets_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks")


# ============================================================
# 💳 STRIPE — checkout.session.completed -> fulfill
# ============================================================

@router.post("/stripe")
async def stripe_webhook(request: Request, background: BackgroundTasks):
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET")

    if not secret:
        logger.error("STRIPE_WEBHOOK_SECRET is not set")
        raise HTTPException(status_code=500, detail="Webhook not configured")

    try:
        event = stripe_lib.Webhook.construct_event(payload, signature, secret)
    except Exception:
        # Wrong signature or malformed payload — not from Stripe. Reject.
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "checkout.session.completed":
        session_id = event["data"]["object"]["id"]
        # handle_payment_return is idempotent (payment_fulfillments table),
        # so webhook + legacy redirect both firing is safe.
        background.add_task(_fulfill_checkout, session_id)

    # Acknowledge everything we don't explicitly handle — otherwise Stripe
    # retries for days and floods the log.
    return {"received": True}


def _fulfill_checkout(session_id: str):
    try:
        ok, msg = payment_engine.handle_payment_return(session_id)
        logger.info(f"Webhook fulfillment for {session_id}: ok={ok} msg={msg}")
        if not ok and msg != "Already Fulfilled":
            database.log_event("system", "Webhook Fulfillment FAILED",
                               {"session_id": session_id, "reason": msg})
    except Exception as e:
        # logger.exception logs the FULL traceback, not just str(e)
        logger.exception(f"Webhook fulfillment crashed for {session_id}")
        try:
            database.log_event("system", "Webhook Fulfillment CRASHED",
                               {"session_id": session_id, "error": repr(e)})
        except Exception:
            logger.exception("Also failed to write crash to audit log")


# ============================================================
# 📞 TWILIO — recording ready -> download -> transcribe -> draft
# ============================================================

def _verify_twilio(request: Request, params: dict):
    """Reject anything that is not a signed Twilio request. Twilio signs the
    FULL url including our query string, so this works for the review
    callbacks too."""
    token = secrets_manager.get_secret("twilio.auth_token")
    signature = request.headers.get("X-Twilio-Signature", "")
    url = str(request.url)
    # Cloud Run terminates TLS; reconstruct the https URL Twilio signed.
    if request.headers.get("x-forwarded-proto") == "https" and url.startswith("http://"):
        url = "https://" + url[len("http://"):]

    if token:
        validator = RequestValidator(token)
        if not validator.validate(url, params, signature):
            logger.warning("Rejected Twilio callback with bad signature")
            raise HTTPException(status_code=403, detail="Invalid Twilio signature")
    else:
        logger.error("twilio.auth_token missing — cannot verify callback")
        raise HTTPException(status_code=500, detail="Twilio not configured")


# ============================================================
# 📞 TWILIO — in-call review: hear it back, keep it or record again
# ============================================================
# <Record action=...> lands here when a take ends. Whatever TwiML we return
# continues the live call, so this is where the redo offer happens.
#
# Only this flow decides which take becomes the letter. The per-recording
# status callback carries mode=safety and does no processing, because it
# fires for discarded takes too.

def _xml(text: str) -> str:
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _twiml(body: str) -> PlainTextResponse:
    return PlainTextResponse(f'<?xml version="1.0" encoding="UTF-8"?><Response>{body}</Response>',
                             media_type="application/xml")


def _say(text: str) -> str:
    return f'<Say voice="{ai_engine.VOICE}">{text}</Say>'


@router.post("/twilio/review")
async def twilio_review(request: Request, background: BackgroundTasks):
    """A take just ended. Play it back and offer a redo."""
    form = await request.form()
    params = {k: v for k, v in form.items()}
    _verify_twilio(request, params)

    q = request.query_params
    kind = q.get("kind", "")
    ref = q.get("ref", "0")
    take = int(q.get("take", "1") or 1)
    max_seconds = int(q.get("max", "600") or 600)

    call_sid = params.get("CallSid")
    recording_url = params.get("RecordingUrl") or ""
    duration = int(params.get("RecordingDuration") or 0)
    digits = params.get("Digits") or ""

    # Hung up instead of pressing #: they are gone, so keep what we have.
    if digits == "hangup" or not recording_url:
        if recording_url and duration > 0:
            background.add_task(_process_recording, call_sid, recording_url)
            database.log_event("system", "Take Kept On Hangup",
                               {"call_sid": call_sid, "kind": kind, "ref": ref, "take": take})
        return _twiml("")

    decide = (f"{ai_engine.callback_base()}/webhooks/twilio/review/decide"
              f"?kind={kind}&ref={ref}&take={take}&max={max_seconds}"
              f"&url={quote(recording_url, safe='')}")

    last_take = take >= ai_engine.MAX_TAKES
    offer = ("Press 1 to send it. Press 2 to record it again." if not last_take
             else "Press 1 to send it. This was your last recording.")

    body = (
        _say("Here is what you recorded.")
        + '<Pause length="1"/>'
        + f'<Play>{_xml(recording_url)}.mp3</Play>'
        + '<Pause length="1"/>'
        + f'<Gather numDigits="1" timeout="8" method="POST" action="{_xml(decide)}">'
        + _say(offer)
        + '</Gather>'
        # No key pressed: silence means keep it.
        + f'<Redirect method="POST">{_xml(decide)}&amp;Digits=1</Redirect>'
    )
    return _twiml(body)


@router.post("/twilio/review/decide")
async def twilio_review_decide(request: Request, background: BackgroundTasks):
    """1 (or silence) keeps the take; 2 records another one."""
    form = await request.form()
    params = {k: v for k, v in form.items()}
    _verify_twilio(request, params)

    q = request.query_params
    kind = q.get("kind", "")
    ref = q.get("ref", "0")
    take = int(q.get("take", "1") or 1)
    max_seconds = int(q.get("max", "600") or 600)
    recording_url = unquote(q.get("url", "") or "")
    digits = (params.get("Digits") or q.get("Digits") or "1").strip()
    call_sid = params.get("CallSid")

    if digits == "2" and take < ai_engine.MAX_TAKES:
        database.log_event("system", "Take Discarded",
                           {"call_sid": call_sid, "kind": kind, "ref": ref, "take": take})
        body = (
            _say("No problem. Let's try that again. "
                 "Speak after the beep, and press the pound key when you are finished.")
            + '<Pause length="1"/>'
            + ai_engine.record_block(kind, ref, take=take + 1, max_seconds=max_seconds)
            + _say("Thank you. Goodbye.")
        )
        return _twiml(body)

    # Keep it — this is the one and only take that gets processed.
    if recording_url and call_sid:
        background.add_task(_process_recording, call_sid, recording_url)
        database.log_event("system", "Take Kept",
                           {"call_sid": call_sid, "kind": kind, "ref": ref, "take": take})
    return _twiml(_say(_goodbye(kind, ref)))


def _goodbye(kind, ref):
    """The sign-off the caller hears. The prospect script's personalised
    farewell lived after <Record>, which no longer runs now that the action
    URL takes over the call — so rebuild it here."""
    if kind == "prospect":
        try:
            letter = database.get_prospect_letter(int(ref)) or {}
            page = database.get_advisor_page_by_email(letter.get("advisor_email") or "") or {}
            recipient = letter.get("recipient_name")
            advisor = page.get("display_name")
            if recipient and advisor:
                return (f"Thank you. Your letter for {_xml(recipient)} will be printed and "
                        f"mailed, with the compliments of {_xml(advisor)}. Goodbye.")
        except Exception:
            logger.exception(f"Goodbye lookup failed for prospect letter {ref}")
    return "Thank you. Your story has been saved. Goodbye."


@router.post("/twilio/recording")
async def twilio_recording(request: Request, background: BackgroundTasks):
    form = await request.form()
    params = {k: v for k, v in form.items()}

    _verify_twilio(request, params)

    call_sid = params.get("CallSid")
    recording_url = params.get("RecordingUrl")

    # Every take fires this callback, including ones the caller threw away.
    # In safety mode we only record that it exists — /twilio/review decides
    # which take becomes the letter.
    if request.query_params.get("mode") == "safety":
        database.log_event("system", "Recording Available",
                           {"call_sid": call_sid, "url": recording_url,
                            "sid": params.get("RecordingSid"),
                            "seconds": params.get("RecordingDuration")})
        return PlainTextResponse("OK")

    if call_sid and recording_url:
        background.add_task(_process_recording, call_sid, recording_url)

    # TwiML-friendly empty 200
    return PlainTextResponse("OK")


def _process_recording(call_sid: str, recording_url: str):
    """Download the recording, transcribe it, attach to the waiting draft.

    Mirrors ai_engine.find_and_transcribe_recording, but PUSH instead of
    the old 'Check for New Stories' PULL.
    """
    audio_url = recording_url if recording_url.endswith(".mp3") else recording_url + ".mp3"
    sid = secrets_manager.get_secret("twilio.account_sid")
    token = secrets_manager.get_secret("twilio.auth_token")

    transcript = "[Audio captured. Transcription unavailable.]"
    tmp_path = f"/tmp/rec_{call_sid}.mp3"

    # Twilio hands us the RecordingUrl the moment the take ENDS, but the media
    # is not fetchable for a few seconds after that — an immediate GET 404s.
    # The review flow processes on that callback (it has to; it is the only
    # place that knows which take the caller kept), so wait for the media
    # rather than writing the placeholder transcript over a real story.
    resp = None
    for attempt in range(6):
        try:
            resp = requests.get(audio_url, auth=(sid, token), timeout=60)
        except Exception:
            logger.exception(f"Recording fetch error for {call_sid}")
            resp = None
        if resp is not None and resp.status_code == 200:
            break
        code = getattr(resp, "status_code", "no response")
        logger.warning(f"Recording not ready ({code}) for {call_sid}, attempt {attempt + 1}/6")
        time.sleep(2)

    try:
        if resp is not None and resp.status_code == 200:
            with open(tmp_path, "wb") as f:
                f.write(resp.content)
            try:
                result = ai_engine.transcribe_audio(tmp_path)
                if result:
                    transcript = result
            finally:
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
        else:
            logger.error("Recording download failed "
                         f"({getattr(resp, 'status_code', 'no response')}) for {call_sid} "
                         "after 6 attempts")
    except Exception:
        logger.exception(f"Recording processing error for {call_sid}")

    # Attach to the project/draft created when the call was triggered
    if database.update_draft_by_sid(call_sid, transcript, audio_url):
        database.log_event("system", "Recording Processed",
                           {"call_sid": call_sid, "chars": len(transcript)})
        return

    # Prospect acquisition path: the SID may belong to a prospect letter.
    # Same recording plumbing; different finish (auto-polish -> print queue).
    letter_id = database.update_prospect_by_sid(call_sid, transcript, audio_url)
    if letter_id:
        from app.prospect import finalize_recording
        try:
            status = finalize_recording(letter_id)
        except Exception:
            logger.exception(f"Prospect finalize crashed for letter {letter_id}")
            status = "error"
        database.log_event("system", "Prospect Recording Processed",
                           {"call_sid": call_sid, "letter_id": letter_id,
                            "chars": len(transcript), "status": status})
        return

    # No draft waiting for this SID — keep the data, flag for admin.
    database.log_event("system", "Orphan Recording",
                       {"call_sid": call_sid, "url": audio_url})
