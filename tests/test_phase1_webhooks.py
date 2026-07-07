"""
Phase 1 regression tests: Stripe webhook, Twilio recording callback, QR player.
External services (Stripe, Twilio, DB) are mocked — CI needs no credentials.
Run:  python -m pytest tests/test_phase1_webhooks.py -v
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("ENV", "staging")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_testsecret")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


# ============================================================
# 💳 Stripe webhook
# ============================================================

def _fake_event(event_type="checkout.session.completed", session_id="cs_test_123"):
    return {"type": event_type, "data": {"object": {"id": session_id}}}


def test_stripe_webhook_rejects_bad_signature():
    r = client.post("/webhooks/stripe", content=b"{}",
                    headers={"stripe-signature": "t=1,v1=garbage"})
    assert r.status_code == 400


def test_stripe_webhook_fulfills_completed_checkout():
    with patch("app.webhooks.stripe_lib.Webhook.construct_event",
               return_value=_fake_event()) as mock_construct, \
         patch("app.webhooks.payment_engine.handle_payment_return",
               return_value=(True, "Credit Added")) as mock_fulfill:
        r = client.post("/webhooks/stripe", content=b"{}",
                        headers={"stripe-signature": "t=1,v1=valid"})
        assert r.status_code == 200
        assert r.json() == {"received": True}
        mock_construct.assert_called_once()
        # BackgroundTasks run before TestClient returns
        mock_fulfill.assert_called_once_with("cs_test_123")


def test_stripe_webhook_ignores_unhandled_event_types():
    with patch("app.webhooks.stripe_lib.Webhook.construct_event",
               return_value=_fake_event(event_type="invoice.created")), \
         patch("app.webhooks.payment_engine.handle_payment_return") as mock_fulfill:
        r = client.post("/webhooks/stripe", content=b"{}",
                        headers={"stripe-signature": "t=1,v1=valid"})
        assert r.status_code == 200
        mock_fulfill.assert_not_called()


def test_stripe_webhook_fulfillment_failure_is_logged_not_raised():
    with patch("app.webhooks.stripe_lib.Webhook.construct_event",
               return_value=_fake_event()), \
         patch("app.webhooks.payment_engine.handle_payment_return",
               return_value=(False, "No Email Found in Transaction")), \
         patch("app.webhooks.database.log_event") as mock_log:
        r = client.post("/webhooks/stripe", content=b"{}",
                        headers={"stripe-signature": "t=1,v1=valid"})
        assert r.status_code == 200  # Stripe must still get its 200
        mock_log.assert_called_once()


# ============================================================
# 📞 Twilio recording callback
# ============================================================

TWILIO_FORM = {
    "CallSid": "CA_test_abc",
    "RecordingUrl": "https://api.twilio.com/2010-04-01/Accounts/AC1/Recordings/RE1",
    "RecordingStatus": "completed",
}


def test_twilio_callback_rejects_bad_signature():
    with patch("app.webhooks.secrets_manager.get_secret", return_value="authtoken"), \
         patch("app.webhooks.RequestValidator") as MockValidator:
        MockValidator.return_value.validate.return_value = False
        r = client.post("/webhooks/twilio/recording", data=TWILIO_FORM,
                        headers={"X-Twilio-Signature": "forged"})
        assert r.status_code == 403


def test_twilio_callback_processes_recording():
    with patch("app.webhooks.secrets_manager.get_secret", return_value="authtoken"), \
         patch("app.webhooks.RequestValidator") as MockValidator, \
         patch("app.webhooks._process_recording") as mock_process:
        MockValidator.return_value.validate.return_value = True
        r = client.post("/webhooks/twilio/recording", data=TWILIO_FORM,
                        headers={"X-Twilio-Signature": "valid"})
        assert r.status_code == 200
        mock_process.assert_called_once_with(
            "CA_test_abc", TWILIO_FORM["RecordingUrl"])


def test_process_recording_attaches_to_draft():
    from app import webhooks

    class FakeResp:
        status_code = 200
        content = b"fake-mp3-bytes"

    with patch("app.webhooks.requests.get", return_value=FakeResp()), \
         patch("app.webhooks.secrets_manager.get_secret", return_value="x"), \
         patch("app.webhooks.ai_engine.transcribe_audio",
               return_value="Once upon a time..."), \
         patch("app.webhooks.database.update_draft_by_sid",
               return_value=True) as mock_update, \
         patch("app.webhooks.database.log_event"):
        webhooks._process_recording("CA_test_abc", TWILIO_FORM["RecordingUrl"])
        mock_update.assert_called_once()
        args = mock_update.call_args[0]
        assert args[0] == "CA_test_abc"
        assert args[1] == "Once upon a time..."
        assert args[2].endswith(".mp3")


def test_process_recording_orphan_is_logged():
    class FakeResp:
        status_code = 200
        content = b"fake-mp3-bytes"

    from app import webhooks
    with patch("app.webhooks.requests.get", return_value=FakeResp()), \
         patch("app.webhooks.secrets_manager.get_secret", return_value="x"), \
         patch("app.webhooks.ai_engine.transcribe_audio", return_value="text"), \
         patch("app.webhooks.database.update_draft_by_sid", return_value=False), \
         patch("app.webhooks.database.log_event") as mock_log:
        webhooks._process_recording("CA_unknown", TWILIO_FORM["RecordingUrl"])
        assert mock_log.call_args[0][1] == "Orphan Recording"


# ============================================================
# 💳 Stripe object compatibility (stripe-python v15 removed .get)
# ============================================================

class ModernStripeObject:
    """Mimics new stripe-python objects: bracket access works,
    .get() does NOT exist and attribute access raises for unknown keys."""
    def __init__(self, data):
        self._data = data

    def __getitem__(self, k):
        return self._data[k]

    def __getattr__(self, k):
        try:
            return self._data[k]
        except KeyError as err:
            raise AttributeError(*err.args) from err


def test_sget_handles_modern_stripe_objects():
    import payment_engine
    md = ModernStripeObject({"user_email": "x@y.com"})
    assert payment_engine._sget(md, "user_email") == "x@y.com"
    assert payment_engine._sget(md, "missing_key") is None
    assert payment_engine._sget(None, "anything") is None
    assert payment_engine._sget({"a": 1}, "a") == 1  # plain dicts too


# ============================================================
# 🎙️ QR player
# ============================================================

def test_play_demo_renders_player():
    r = client.get("/play/demo")
    assert r.status_code == 200
    assert "Barnaby Jones" in r.text
    assert "<audio" in r.text


def test_play_unknown_story_returns_404_page():
    with patch("app.player.database.get_public_draft", return_value=None):
        r = client.get("/play/999999")
        assert r.status_code == 404
        assert "couldn't find this story" in r.text


def test_play_twilio_audio_is_proxied_not_exposed():
    story = {"url": "https://api.twilio.com/2010-04-01/Accounts/AC1/Recordings/RE1.mp3",
             "title": "Story #7", "date": "July 4, 2026", "storyteller": "Grandma",
             "released": True}
    with patch("app.player.database.get_public_draft", return_value=story):
        r = client.get("/play/7")
        assert r.status_code == 200
        assert "/play/7/audio.mp3" in r.text          # proxy URL in page
        assert "api.twilio.com" not in r.text          # raw URL never leaks


def test_play_audio_proxy_streams_bytes():
    story = {"url": "https://api.twilio.com/2010-04-01/Accounts/AC1/Recordings/RE1.mp3",
             "title": "Story #7", "date": "July 4, 2026", "storyteller": "Grandma",
             "released": True}
    with patch("app.player.database.get_public_draft", return_value=story), \
         patch("app.player.ai_engine.fetch_recording_audio",
               return_value=b"mp3-bytes"):
        r = client.get("/play/7/audio.mp3")
        assert r.status_code == 200
        assert r.headers["content-type"] == "audio/mpeg"
        assert r.content == b"mp3-bytes"


def test_play_unreleased_story_is_locked():
    """B2B recordings stay locked until the advisor releases them —
    the heir's path to the audio runs through the advisor's desk."""
    story = {"url": "https://api.twilio.com/2010/Recordings/RE1.mp3",
             "title": "Story #8", "date": "July 6, 2026",
             "storyteller": "Grandpa", "released": False}
    with patch("app.player.database.get_public_draft", return_value=story):
        page = client.get("/play/8")
        assert page.status_code == 200
        assert "RECORDING IS SECURED" in page.text
        assert "contact the advisor" in page.text
        assert "<audio" not in page.text
        # the raw mp3 proxy must be locked too, not just the page
        audio = client.get("/play/8/audio.mp3")
        assert audio.status_code == 403


def test_play_demo_remains_open():
    r = client.get("/play/demo")
    assert r.status_code == 200
    assert "<audio" in r.text
