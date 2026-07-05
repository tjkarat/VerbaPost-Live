"""
Webhook endpoints — Phase 1.

/webhooks/stripe            Stripe checkout fulfillment (replaces redirect-only flow)
/webhooks/twilio/recording  Twilio recording-complete -> transcribe -> save draft

Both verify cryptographic signatures before trusting anything in the request.
Both hand real work to background tasks so the caller gets a fast 200
(Stripe and Twilio retry on slow/failed responses — we never want that
to double-process).
"""

import logging
import os
import sys
from pathlib import Path

# Engines live at repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests
import stripe as stripe_lib
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import PlainTextResponse
from twilio.request_validator import RequestValidator

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
        logger.error(f"Webhook fulfillment crashed for {session_id}: {e}")
        database.log_event("system", "Webhook Fulfillment CRASHED",
                           {"session_id": session_id, "error": str(e)})


# ============================================================
# 📞 TWILIO — recording ready -> download -> transcribe -> draft
# ============================================================

@router.post("/twilio/recording")
async def twilio_recording(request: Request, background: BackgroundTasks):
    form = await request.form()
    params = {k: v for k, v in form.items()}

    # --- Verify the request really came from Twilio ---
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

    call_sid = params.get("CallSid")
    recording_url = params.get("RecordingUrl")

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

    try:
        resp = requests.get(audio_url, auth=(sid, token), timeout=60)
        if resp.status_code == 200:
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
            logger.error(f"Recording download failed ({resp.status_code}) for {call_sid}")
    except Exception as e:
        logger.error(f"Recording processing error for {call_sid}: {e}")

    # Attach to the project/draft created when the call was triggered
    if database.update_draft_by_sid(call_sid, transcript, audio_url):
        database.log_event("system", "Recording Processed",
                           {"call_sid": call_sid, "chars": len(transcript)})
    else:
        # No draft waiting for this SID — keep the data, flag for admin.
        database.log_event("system", "Orphan Recording",
                           {"call_sid": call_sid, "url": audio_url})
