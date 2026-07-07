"""
Phase 3 regression tests: advisor portal, heirloom dashboard, heir archive, checkout.
All external services mocked. Run: python -m pytest tests/test_phase3_product.py -v
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("ENV", "staging")
os.environ.setdefault("BASE_URL", "https://staging.verbapost.com")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)

ADVISOR_PROFILE = {"role": "advisor", "full_name": "Ada Advisor",
                   "advisor_firm": "Ada Wealth", "credits": 2}
HEIR_PROFILE = {"role": "heir", "full_name": "Harry Heir", "advisor_firm": "Ada Wealth",
                "credits": 1, "created_by": "ada@wealth.com", "parent_phone": "6155550100",
                "address_line1": "1 Main St", "address_city": "Nashville",
                "address_state": "TN", "address_zip": "37201", "id": 7}


def _login(profile):
    """Returns an authenticated TestClient (https so Secure cookies work)."""
    c = TestClient(app, base_url="https://testserver")
    with patch("app.auth.auth_engine.sign_in", return_value=(MagicMock(), None)), \
         patch("app.auth.database.get_user_profile", return_value=profile):
        c.post("/login", data={"email": "user@test.com", "password": "pw12345678"})
    return c


# ============================================================
# Advisor portal
# ============================================================

def test_advisor_requires_login():
    r = client.get("/advisor", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/login"


def test_advisor_dashboard_renders():
    c = _login(ADVISOR_PROFILE)
    with patch("app.advisor.database.get_user_profile", return_value=ADVISOR_PROFILE), \
         patch("app.advisor.database.fetch_advisor_clients",
               return_value=[{"full_name": "Client One", "email": "c1@x.com"}]), \
         patch("app.advisor.database.get_advisor_projects_for_media", return_value=[]):
        r = c.get("/advisor")
    assert r.status_code == 200
    assert "Ada Wealth" in r.text
    assert "Client One" in r.text
    assert "Purchase Credit ($99)" in r.text


def test_activate_client_deducts_credit_and_emails():
    c = _login(ADVISOR_PROFILE)
    with patch("app.advisor.database.get_user_profile", return_value=dict(ADVISOR_PROFILE)), \
         patch("app.advisor.database.create_sponsored_user",
               return_value=(True, "Success")) as mock_create, \
         patch("app.advisor.database.update_user_credits") as mock_credits, \
         patch("app.advisor.email_engine.send_heir_welcome_email",
               return_value=True) as mock_email, \
         patch("app.advisor.audit_engine.log_event"), \
         patch("app.advisor.database.fetch_advisor_clients", return_value=[]), \
         patch("app.advisor.database.get_advisor_projects_for_media", return_value=[]):
        r = c.post("/advisor/activate",
                   data={"client_name": "Sarah", "client_email": "sarah@x.com"})
    assert r.status_code == 200
    assert "Welcome email sent" in r.text
    mock_create.assert_called_once()
    mock_credits.assert_called_once_with("user@test.com", 1)  # 2 - 1
    mock_email.assert_called_once()


def test_activate_blocked_without_credits():
    broke = dict(ADVISOR_PROFILE, credits=0)
    c = _login(broke)
    with patch("app.advisor.database.get_user_profile", return_value=broke), \
         patch("app.advisor.database.create_sponsored_user") as mock_create, \
         patch("app.advisor.database.fetch_advisor_clients", return_value=[]), \
         patch("app.advisor.database.get_advisor_projects_for_media", return_value=[]):
        r = c.post("/advisor/activate",
                   data={"client_name": "Sarah", "client_email": "sarah@x.com"})
    assert "Insufficient credits" in r.text
    mock_create.assert_not_called()


def test_checkout_redirects_to_stripe():
    c = _login(ADVISOR_PROFILE)
    with patch("app.advisor.database.get_user_profile", return_value=ADVISOR_PROFILE), \
         patch("app.advisor.payment_engine.create_checkout_session",
               return_value="https://checkout.stripe.com/test123") as mock_pay:
        r = c.get("/advisor/checkout", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"].startswith("https://checkout.stripe.com/")
    assert mock_pay.call_args.kwargs["user_email"] == "user@test.com"
    item = mock_pay.call_args.kwargs["line_items"][0]
    assert item["price_data"]["unit_amount"] == 9900


# ============================================================
# Heirloom dashboard
# ============================================================

def test_heirloom_requires_login():
    r = client.get("/heirloom", follow_redirects=False)
    assert r.status_code == 302


def test_heirloom_renders_for_sponsored_heir():
    c = _login(HEIR_PROFILE)
    with patch("app.heirloom.database.get_user_profile", return_value=HEIR_PROFILE), \
         patch("app.heirloom.database.get_user_drafts", return_value=[
             {"id": 42, "content": "Once upon a time", "status": "Draft",
              "created_at": "2026-07-01 10:00:00",
              "tracking_number": "https://api.twilio.com/2010/Recordings/RE9.mp3"}]):
        r = c.get("/heirloom")
    assert r.status_code == 200
    assert "Start a New Interview" in r.text
    assert "Once upon a time" in r.text
    assert "/play/42/audio.mp3" in r.text          # Twilio audio proxied
    assert "api.twilio.com" not in r.text          # never exposed raw


def test_unsponsored_user_sees_guest_mode():
    guest = {"role": "user", "credits": 0}
    c = _login(guest)
    with patch("app.heirloom.database.get_user_profile", return_value=guest):
        r = c.get("/heirloom")
    assert "Account Verification Pending" in r.text


def test_start_call_creates_pending_draft():
    c = _login(HEIR_PROFILE)
    with patch("app.heirloom.database.get_user_profile", return_value=HEIR_PROFILE), \
         patch("app.heirloom.ai_engine.trigger_outbound_call",
               return_value=("CA123", None)) as mock_call, \
         patch("app.heirloom.database.create_draft", return_value=True) as mock_draft, \
         patch("app.heirloom.audit_engine.log_event"), \
         patch("app.heirloom.email_engine.send_advisor_heir_started_alert"):
        r = c.post("/heirloom/call",
                   data={"target_phone": "(615) 555-0100", "question": "Tell me a story"},
                   follow_redirects=False)
    assert r.status_code == 303
    assert "call_started" in r.headers["location"]
    assert mock_call.call_args.kwargs["to_phone"] == "6155550100"
    assert mock_draft.call_args.kwargs["call_sid"] == "CA123"


def test_start_call_rejects_bad_phone():
    c = _login(HEIR_PROFILE)
    with patch("app.heirloom.database.get_user_profile", return_value=HEIR_PROFILE), \
         patch("app.heirloom.ai_engine.trigger_outbound_call") as mock_call:
        r = c.post("/heirloom/call", data={"target_phone": "12345", "question": ""},
                   follow_redirects=False)
    assert "bad_phone" in r.headers["location"]
    mock_call.assert_not_called()


def test_mail_letter_deducts_credit_and_queues():
    c = _login(HEIR_PROFILE)
    with patch("app.heirloom.database.get_user_profile", return_value=dict(HEIR_PROFILE)), \
         patch("app.heirloom.database.update_draft"), \
         patch("app.heirloom.database.update_user_credits") as mock_credits, \
         patch("app.heirloom.database.update_project_details") as mock_status, \
         patch("app.heirloom.audit_engine.log_event"), \
         patch("app.heirloom.email_engine.send_admin_print_ready_alert") as mock_alert:
        r = c.post("/heirloom/draft/42/mail", data={"content": "Final text"},
                   follow_redirects=False)
    assert "queued" in r.headers["location"]
    mock_credits.assert_called_once_with("user@test.com", 0)  # 1 - 1
    mock_status.assert_called_once_with(42, status="Approved")
    mock_alert.assert_called_once()


def test_mail_letter_blocked_without_credits():
    broke = dict(HEIR_PROFILE, credits=0)
    c = _login(broke)
    with patch("app.heirloom.database.get_user_profile", return_value=broke), \
         patch("app.heirloom.database.update_project_details") as mock_status:
        r = c.post("/heirloom/draft/42/mail", data={"content": "x"},
                   follow_redirects=False)
    assert "no_credits" in r.headers["location"]
    mock_status.assert_not_called()


# ============================================================
# Heir archive (QR vault)
# ============================================================

PROJECT = {"id": 9, "firm_name": "Ada Wealth", "heir_name": "Harry",
           "parent_name": "Grandma Rose", "audio_released": True,
           "audio_ref": None,
           "tracking_number": "https://api.twilio.com/2010/Recordings/RE9.mp3"}


def test_archive_renders_released_audio_via_proxy():
    with patch("app.heirloom.database.get_project_by_id", return_value=PROJECT):
        r = client.get("/archive/9")
    assert r.status_code == 200
    assert "Grandma Rose" in r.text
    assert "Ada Wealth" in r.text
    assert "/play/9/audio.mp3" in r.text


def test_archive_locked_audio_hidden():
    locked = dict(PROJECT, audio_released=False)
    with patch("app.heirloom.database.get_project_by_id", return_value=locked):
        r = client.get("/archive/9")
    assert "currently secured" in r.text
    assert "<audio" not in r.text


def test_archive_unknown_id_404s():
    with patch("app.heirloom.database.get_project_by_id", return_value=None):
        r = client.get("/archive/99999")
    assert r.status_code == 404


def test_archive_root_redirects_to_heirloom():
    r = client.get("/archive", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/heirloom"
