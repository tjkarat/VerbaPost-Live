"""
Phase 5 regression tests: prospect acquisition path.

Advisor-branded landing page, consent capture, DNC scrub, outbound call,
recording -> print queue, QR player, CSV send log, pricing + fulfillment,
admin queue/grant. All external services mocked.

Run: python -m pytest tests/test_phase5_prospect.py -v
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("ENV", "staging")
os.environ.setdefault("BASE_URL", "https://staging.verbapost.com")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import dnc_engine  # noqa: E402
import pricing_engine  # noqa: E402
from app.main import app  # noqa: E402
from app import prospect as prospect_mod  # noqa: E402

PAGE = {"id": 1, "advisor_email": "ada@wealth.com", "slug": "ada", "display_name": "Ada Advisor",
        "firm_name": "Ada Wealth", "headline": None, "intro": None, "prompt": None,
        "photo_data": None, "photo_mime": None, "disclosure": "Securities via Example LLC.",
        "return_line1": "9 Money Ln", "return_city": "Nashville", "return_state": "TN",
        "return_zip": "37203", "active": True}

GOOD_FORM = {"prospect_name": "Pat Prospect", "phone": "(615) 555-0142",
             "recipient_name": "Sam Recipient", "line1": "12 Oak St", "city": "Franklin",
             "state": "tn", "zip_code": "37064", "consent": "yes",
             "consent_version": dnc_engine.CONSENT_VERSION, "website": ""}

ADVISOR_PROFILE = {"role": "advisor", "full_name": "Ada Advisor",
                   "advisor_firm": "Ada Wealth", "credits": 0}


def _client():
    return TestClient(app, base_url="https://testserver")


def _page_patches(available=5, dupe=None):
    return [
        patch("app.prospect.database.get_advisor_page_by_slug", return_value=dict(PAGE)),
        patch("app.prospect.database.prospect_letters_available", return_value=available),
        patch("app.prospect.database.find_recent_prospect_by_phone", return_value=dupe),
        patch("app.prospect.audit_engine.log_event"),
    ]


class _Stack:
    def __init__(self, patches):
        self.patches = patches
        self.mocks = []

    def __enter__(self):
        self.mocks = [p.__enter__() for p in self.patches]
        return self.mocks

    def __exit__(self, *a):
        for p in reversed(self.patches):
            p.__exit__(*a)


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    prospect_mod._hits.clear()
    yield
    prospect_mod._hits.clear()


# ============================================================
# dnc_engine unit tests
# ============================================================

def test_normalize_phone_variants():
    assert dnc_engine.normalize_phone("(615) 555-0142") == "+16155550142"
    assert dnc_engine.normalize_phone("1-615-555-0142") == "+16155550142"
    assert dnc_engine.normalize_phone("+1 615 555 0142") == "+16155550142"
    assert dnc_engine.normalize_phone("615555014") is None          # 9 digits
    assert dnc_engine.normalize_phone("015-555-0142") is None       # bad area code
    assert dnc_engine.normalize_phone("") is None


def test_consent_text_names_advisor_and_firm():
    txt = dnc_engine.consent_text_for("Ada Advisor", "Ada Wealth")
    assert "Ada Advisor of Ada Wealth" in txt
    assert "express written consent" in txt
    assert "artificial voice" in txt
    assert "not a condition of any purchase" in txt


def test_scrub_internal_only_without_provider(monkeypatch):
    monkeypatch.delenv("DNC_PROVIDER_URL", raising=False)
    with patch("dnc_engine.database.is_dnc_suppressed", return_value=False):
        r = dnc_engine.scrub("+16155550142")
    assert r["status"] == "internal_only"
    assert dnc_engine.may_dial(r)


def test_scrub_internal_listed_wins(monkeypatch):
    monkeypatch.setenv("DNC_PROVIDER_URL", "https://dnc.example/check/{phone}")
    with patch("dnc_engine.database.is_dnc_suppressed", return_value=True), \
         patch("dnc_engine.requests.get") as get:
        r = dnc_engine.scrub("+16155550142")
    assert r["status"] == "listed"
    assert not dnc_engine.may_dial(r)
    get.assert_not_called()   # never bothered the vendor


def test_scrub_external_provider_clear_and_listed(monkeypatch):
    monkeypatch.setenv("DNC_PROVIDER_URL", "https://dnc.example/check/{phone}")
    monkeypatch.setenv("DNC_PROVIDER_NAME", "vendorx")
    monkeypatch.setenv("DNC_PROVIDER_KEY", "k")
    resp = MagicMock(); resp.json.return_value = {"on_dnc": False}
    with patch("dnc_engine.database.is_dnc_suppressed", return_value=False), \
         patch("dnc_engine.requests.get", return_value=resp) as get:
        r = dnc_engine.scrub("+16155550142")
    assert r["status"] == "clear" and "vendorx" in r["provider"]
    assert get.call_args[0][0].endswith("/check/+16155550142")
    assert get.call_args[1]["headers"]["Authorization"] == "Bearer k"
    resp.json.return_value = {"result": {"on_dnc": True}}
    with patch("dnc_engine.database.is_dnc_suppressed", return_value=False), \
         patch("dnc_engine.requests.get", return_value=resp):
        r = dnc_engine.scrub("+16155550142")
    assert r["status"] == "listed"


def test_scrub_provider_error_fail_closed_by_default(monkeypatch):
    monkeypatch.setenv("DNC_PROVIDER_URL", "https://dnc.example/check")
    monkeypatch.delenv("DNC_FAIL_CLOSED", raising=False)
    with patch("dnc_engine.database.is_dnc_suppressed", return_value=False), \
         patch("dnc_engine.requests.post", side_effect=RuntimeError("down")):
        r = dnc_engine.scrub("+16155550142")
    assert r["status"] == "error"
    assert not dnc_engine.may_dial(r)
    monkeypatch.setenv("DNC_FAIL_CLOSED", "0")
    assert dnc_engine.may_dial(r)


# ============================================================
# Landing page
# ============================================================

def test_landing_renders_advisor_branding_and_consent():
    with _Stack(_page_patches(available=5)):
        r = _client().get("/a/ada")
    assert r.status_code == 200
    assert "Ada Advisor" in r.text and "Ada Wealth" in r.text
    assert "Securities via Example LLC." in r.text
    assert 'name="consent" value="yes"' in r.text
    assert dnc_engine.CONSENT_VERSION in r.text
    assert "express written consent" in r.text
    assert 'name="website"' in r.text            # honeypot present
    assert "For Advisors" not in r.text          # VerbaPost nav replaced by advisor header


def test_landing_closes_at_zero_balance():
    with _Stack(_page_patches(available=0)):
        r = _client().get("/a/ada")
    assert r.status_code == 200
    assert "currently closed" in r.text
    assert 'name="consent"' not in r.text


def test_landing_unknown_or_paused_slug_404():
    with patch("app.prospect.database.get_advisor_page_by_slug", return_value=None):
        assert _client().get("/a/nobody").status_code == 404
    paused = dict(PAGE, active=False)
    with patch("app.prospect.database.get_advisor_page_by_slug", return_value=paused):
        assert _client().get("/a/ada").status_code == 404


# ============================================================
# Intake -> consent -> DNC -> dial
# ============================================================

def test_intake_requires_consent_checkbox():
    form = dict(GOOD_FORM, consent="")
    with _Stack(_page_patches()):
        r = _client().post("/a/ada", data=form, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].endswith("?m=no_consent")


def test_intake_rejects_stale_consent_version():
    form = dict(GOOD_FORM, consent_version="old")
    with _Stack(_page_patches()):
        r = _client().post("/a/ada", data=form, follow_redirects=False)
    assert r.headers["location"].endswith("?m=no_consent")


def test_intake_validation_messages():
    cases = [("phone", "12", "bad_phone"), ("prospect_name", "", "bad_name"),
             ("state", "Tennessee", "bad_state"), ("zip_code", "12", "bad_zip"),
             ("line1", "", "bad_recipient")]
    for field, value, code in cases:
        with _Stack(_page_patches()):
            r = _client().post("/a/ada", data=dict(GOOD_FORM, **{field: value}), follow_redirects=False)
        assert r.headers["location"].endswith(f"?m={code}"), field


def test_intake_honeypot_never_dials():
    with _Stack(_page_patches()), \
         patch("app.prospect.database.create_prospect_letter") as create, \
         patch("app.prospect.ai_engine.trigger_prospect_call") as call:
        r = _client().post("/a/ada", data=dict(GOOD_FORM, website="http://spam"), follow_redirects=False)
    assert r.status_code == 303
    create.assert_not_called(); call.assert_not_called()


def test_intake_closed_and_dupe():
    with _Stack(_page_patches(available=0)), \
         patch("app.prospect.database.create_prospect_letter") as create:
        r = _client().post("/a/ada", data=GOOD_FORM, follow_redirects=False)
    assert r.headers["location"].endswith("?m=closed"); create.assert_not_called()
    with _Stack(_page_patches(available=3, dupe={"id": 4})), \
         patch("app.prospect.database.create_prospect_letter") as create:
        r = _client().post("/a/ada", data=GOOD_FORM, follow_redirects=False)
    assert r.headers["location"].endswith("?m=dupe"); create.assert_not_called()


def test_intake_rate_limit_per_ip():
    with _Stack(_page_patches()), \
         patch("app.prospect.database.create_prospect_letter", return_value=None):
        c = _client()
        codes = []
        for _ in range(prospect_mod.RATE_LIMIT_PER_IP + 1):
            r = c.post("/a/ada", data=GOOD_FORM, follow_redirects=False)
            codes.append(r.headers["location"].split("m=")[-1])
    assert codes[-1] == "rate" and "rate" not in codes[:-1]


def test_intake_happy_path_records_consent_scrubs_and_dials():
    scrub = {"status": "internal_only", "provider": "internal",
             "checked_at": datetime(2026, 9, 8, 12, 0, 0), "detail": ""}
    with _Stack(_page_patches()), \
         patch("app.prospect.database.create_prospect_letter", return_value=42) as create, \
         patch("app.prospect.database.update_prospect_letter") as update, \
         patch("app.prospect.database.get_prospect_letter", return_value={"call_attempts": 0}), \
         patch("app.prospect.dnc_engine.scrub", return_value=scrub) as scrub_fn, \
         patch("app.prospect.ai_engine.trigger_prospect_call", return_value=("CA123", None)) as call:
        c = _client()
        r = c.post("/a/ada", data=GOOD_FORM, headers={"x-forwarded-for": "203.0.113.9, 10.0.0.1",
                                                      "user-agent": "pytest-ua"},
                   follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"] == "/a/ada/thanks/42"

        # consent record written BEFORE the dial, with every audit field
        kw = create.call_args.kwargs
        assert kw["prospect_phone"] == "+16155550142"
        assert kw["recipient_state"] == "TN"
        assert kw["consent_version"] == dnc_engine.CONSENT_VERSION
        assert "Ada Advisor of Ada Wealth" in kw["consent_text"]
        assert kw["consent_ip"] == "203.0.113.9" and kw["consent_user_agent"] == "pytest-ua"
        assert kw["status"] == "consented"

        # scrubbed the normalized number, then dialed with the prospect script
        scrub_fn.assert_called_once_with("+16155550142")
        call.assert_called_once()
        ck = call.call_args.kwargs
        assert ck["to_phone"] == "+16155550142" and ck["advisor_name"] == "Ada Advisor"
        assert ck["recipient_name"] == "Sam Recipient" and ck["prospect_name"] == "Pat Prospect"
        statuses = [c_.kwargs.get("status") for c_ in update.call_args_list if "status" in c_.kwargs]
        assert statuses[-1] == "calling"
        dnc_writes = [c_.kwargs for c_ in update.call_args_list if "dnc_status" in c_.kwargs]
        assert dnc_writes and dnc_writes[0]["dnc_status"] == "internal_only"

        # confirmation page is bound to this browser session
        letter = {"id": 42, "advisor_email": "ada@wealth.com", "status": "calling",
                  "recipient_name": "Sam Recipient", "prospect_name": "Pat", "call_attempts": 1,
                  "prospect_phone": "+16155550142", "last_call_at": datetime.utcnow()}
        with patch("app.prospect.database.get_prospect_letter", return_value=letter):
            r = c.get("/a/ada/thanks/42")
            assert r.status_code == 200 and "about to ring" in r.text
            assert "Sam Recipient" in r.text and "Call me again" in r.text
            # a different browser can't see it
            r2 = _client().get("/a/ada/thanks/42", follow_redirects=False)
            assert r2.status_code == 302


def test_intake_dnc_listed_blocks_dial():
    scrub = {"status": "listed", "provider": "internal", "checked_at": datetime.utcnow(), "detail": ""}
    with _Stack(_page_patches()), \
         patch("app.prospect.database.create_prospect_letter", return_value=7), \
         patch("app.prospect.database.update_prospect_letter") as update, \
         patch("app.prospect.dnc_engine.scrub", return_value=scrub), \
         patch("app.prospect.ai_engine.trigger_prospect_call") as call:
        c = _client()
        r = c.post("/a/ada", data=GOOD_FORM, follow_redirects=False)
        assert r.headers["location"] == "/a/ada/thanks/7"
        call.assert_not_called()
        assert any(k.kwargs.get("status") == "dnc_blocked" for k in update.call_args_list)
        letter = {"id": 7, "advisor_email": "ada@wealth.com", "status": "dnc_blocked",
                  "recipient_name": "Sam", "prospect_name": "Pat", "call_attempts": 0}
        with patch("app.prospect.database.get_prospect_letter", return_value=letter):
            r = c.get("/a/ada/thanks/7")
    assert "do-not-call" in r.text


def test_redial_respects_cooldown_and_max_attempts():
    with _Stack(_page_patches()), \
         patch("app.prospect.database.create_prospect_letter", return_value=9), \
         patch("app.prospect.database.update_prospect_letter"), \
         patch("app.prospect.database.get_prospect_letter", return_value={"call_attempts": 0}), \
         patch("app.prospect.dnc_engine.scrub", return_value={"status": "internal_only", "provider": "internal", "checked_at": datetime.utcnow()}), \
         patch("app.prospect.ai_engine.trigger_prospect_call", return_value=("CA1", None)) as call:
        c = _client()
        c.post("/a/ada", data=GOOD_FORM, follow_redirects=False)
        base = {"id": 9, "advisor_email": "ada@wealth.com", "status": "calling", "prospect_phone": "+16155550142",
                "prospect_name": "Pat", "recipient_name": "Sam"}
        # too soon
        with patch("app.prospect.database.get_prospect_letter",
                   return_value=dict(base, call_attempts=1, last_call_at=datetime.utcnow())):
            r = c.post("/a/ada/again/9", follow_redirects=False)
        assert r.headers["location"].endswith("?m=cooldown")
        # cooled down -> dials again
        with patch("app.prospect.database.get_prospect_letter",
                   return_value=dict(base, call_attempts=1, last_call_at=datetime.utcnow() - timedelta(minutes=5))):
            r = c.post("/a/ada/again/9", follow_redirects=False)
        assert r.headers["location"] == "/a/ada/thanks/9" and call.call_count == 2
        # exhausted
        with patch("app.prospect.database.get_prospect_letter",
                   return_value=dict(base, call_attempts=3, last_call_at=datetime.utcnow() - timedelta(minutes=5))):
            r = c.post("/a/ada/again/9", follow_redirects=False)
        assert r.headers["location"].endswith("?m=max_attempts") and call.call_count == 2


def test_opt_out_adds_internal_dnc_and_closes_request():
    with _Stack(_page_patches()), \
         patch("app.prospect.database.create_prospect_letter", return_value=11), \
         patch("app.prospect.database.update_prospect_letter") as update, \
         patch("app.prospect.database.get_prospect_letter", return_value={"call_attempts": 0}), \
         patch("app.prospect.dnc_engine.scrub", return_value={"status": "internal_only", "provider": "internal", "checked_at": datetime.utcnow()}), \
         patch("app.prospect.ai_engine.trigger_prospect_call", return_value=("CA1", None)), \
         patch("app.prospect.dnc_engine.opt_out") as opt:
        c = _client()
        c.post("/a/ada", data=GOOD_FORM, follow_redirects=False)
        letter = {"id": 11, "advisor_email": "ada@wealth.com", "status": "calling", "prospect_phone": "+16155550142"}
        with patch("app.prospect.database.get_prospect_letter", return_value=letter):
            r = c.post("/a/ada/opt-out/11", follow_redirects=False)
    assert r.headers["location"].endswith("?m=opted_out")
    opt.assert_called_once()
    assert opt.call_args[0][0] == "+16155550142"
    assert any(k.kwargs.get("status") == "opted_out" for k in update.call_args_list)


# ============================================================
# Recording -> letter (webhook + finalize)
# ============================================================

def _twilio_post(sid="CAprospect", url="https://api.twilio.com/rec/RE1"):
    with patch("app.webhooks.secrets_manager.get_secret", return_value="tok"), \
         patch("app.webhooks.RequestValidator") as rv:
        rv.return_value.validate.return_value = True
        with patch("app.webhooks._process_recording") as proc:
            r = TestClient(app).post("/webhooks/twilio/recording",
                                     data={"CallSid": sid, "RecordingUrl": url})
    return r, proc


def test_webhook_routes_prospect_sid_to_finalize():
    resp = MagicMock(status_code=200, content=b"mp3")
    with patch("app.webhooks.requests.get", return_value=resp), \
         patch("app.webhooks.secrets_manager.get_secret", return_value="x"), \
         patch("app.webhooks.ai_engine.transcribe_audio", return_value="A long story about the lake house and the summer of 1971."), \
         patch("app.webhooks.database.update_draft_by_sid", return_value=False), \
         patch("app.webhooks.database.update_prospect_by_sid", return_value=42) as upd, \
         patch("app.prospect.finalize_recording", return_value="Approved") as fin, \
         patch("app.webhooks.database.log_event") as log:
        from app.webhooks import _process_recording
        _process_recording("CAprospect", "https://api.twilio.com/rec/RE1")
    upd.assert_called_once()
    assert upd.call_args[0][0] == "CAprospect" and upd.call_args[0][2].endswith(".mp3")
    fin.assert_called_once_with(42)
    assert log.call_args[0][1] == "Prospect Recording Processed"


def test_finalize_recording_polishes_and_queues_without_extra_billing():
    letter = {"id": 42, "status": "recorded", "advisor_email": "ada@wealth.com",
              "transcript_raw": "Um, so, when your grandmother and I first met at the lake house in 1971...",
              "prospect_name": "Pat", "recipient_name": "Sam", "recipient_line1": "12 Oak",
              "recipient_city": "Franklin", "recipient_state": "TN", "recipient_zip": "37064"}
    with patch("app.prospect.database.get_prospect_letter", return_value=letter), \
         patch("app.prospect.ai_engine.refine_text", return_value="When your grandmother and I first met...") as refine, \
         patch("app.prospect.database.update_prospect_letter") as update, \
         patch("app.prospect.database.add_prospect_credits") as ledger, \
         patch("app.prospect.database.get_advisor_page_by_email", return_value=dict(PAGE)), \
         patch("app.prospect.database.prospect_credit_balance", return_value=24), \
         patch("app.prospect.audit_engine.log_event"), \
         patch("email_engine.send_admin_print_ready_alert") as admin_mail, \
         patch("email_engine.send_advisor_prospect_letter_alert") as adv_mail:
        status = prospect_mod.finalize_recording(42)
    assert status == "Approved"
    refine.assert_called_once()
    kw = update.call_args.kwargs
    assert kw["status"] == "Approved" and kw["letter_text"].startswith("When your")
    assert kw["letter_version"] == prospect_mod.LETTER_VERSION
    # The story letter is INCLUDED with the invitation that produced it —
    # billing happens once, when the invitation is mailed.
    ledger.assert_not_called()
    admin_mail.assert_called_once()
    assert admin_mail.call_args.kwargs["mailing_list"][0]["name"] == "Sam"
    adv_mail.assert_called_once()
    assert adv_mail.call_args.kwargs["letters_left"] == 24


def test_finalize_recording_too_short_consumes_nothing():
    letter = {"id": 43, "status": "recorded", "advisor_email": "ada@wealth.com",
              "transcript_raw": "Hello? Hello."}
    with patch("app.prospect.database.get_prospect_letter", return_value=letter), \
         patch("app.prospect.ai_engine.refine_text") as refine, \
         patch("app.prospect.database.update_prospect_letter") as update, \
         patch("app.prospect.database.add_prospect_credits") as ledger, \
         patch("app.prospect.audit_engine.log_event"):
        status = prospect_mod.finalize_recording(43)
    assert status == "recording_too_short"
    refine.assert_not_called(); ledger.assert_not_called()
    assert update.call_args.kwargs["status"] == "recording_too_short"


def test_finalize_is_idempotent_on_status():
    with patch("app.prospect.database.get_prospect_letter", return_value={"id": 1, "status": "Approved"}), \
         patch("app.prospect.database.add_prospect_credits") as ledger:
        assert prospect_mod.finalize_recording(1) == "Approved"
    ledger.assert_not_called()


# ============================================================
# QR player for prospect letters
# ============================================================

def test_player_serves_prospect_letter_audio_via_proxy():
    letter = {"id": 42, "status": "Approved", "audio_url": "https://api.twilio.com/x/RE1.mp3",
              "prospect_name": "Pat Prospect", "created_at": datetime(2026, 9, 8)}
    with patch("app.player.database.get_prospect_letter", return_value=letter):
        r = TestClient(app).get("/play/p42")
        assert r.status_code == 200
        assert "Pat Prospect" in r.text and "/play/p42/audio.mp3" in r.text
        with patch("app.player.ai_engine.fetch_recording_audio", return_value=b"ID3"):
            a = TestClient(app).get("/play/p42/audio.mp3")
    assert a.status_code == 200 and a.headers["content-type"].startswith("audio/mpeg")


def test_player_hides_prospect_letter_until_approved():
    letter = {"id": 42, "status": "calling", "audio_url": None, "prospect_name": "Pat"}
    with patch("app.player.database.get_prospect_letter", return_value=letter):
        assert TestClient(app).get("/play/p42").status_code == 404


def test_root_legacy_play_param_redirects_prefixed_id():
    r = TestClient(app).get("/?play=p42&utm_source=physical_mail", follow_redirects=False)
    assert r.status_code == 301 and r.headers["location"] == "/play/p42"


# ============================================================
# Pricing, checkout, fulfillment
# ============================================================

def test_prospect_quote_first_then_repeat():
    q = pricing_engine.prospect_quote(False, letters=100)
    assert q["kind"] == "first_campaign" and q["letters"] == 25 and q["total_cents"] == 50000
    q = pricing_engine.prospect_quote(True, letters=7)
    assert q["kind"] == "repeat" and q["letters"] == 7 and q["total_cents"] == 14000
    q = pricing_engine.prospect_quote(True, letters=0)
    assert q["letters"] == 1
    q = pricing_engine.prospect_quote(True, letters="abc")
    assert q["letters"] == 1


def _advisor_client():
    c = _client()
    with patch("app.auth.auth_engine.sign_in", return_value=(MagicMock(), None)), \
         patch("app.auth.database.get_user_profile", return_value=ADVISOR_PROFILE):
        c.post("/login", data={"email": "ada@wealth.com", "password": "pw12345678"})
    return c


def test_checkout_first_campaign_is_flat_500_for_25():
    c = _advisor_client()
    with patch("app.advisor.database.get_user_profile", return_value=ADVISOR_PROFILE), \
         patch("app.advisor.database.prospect_has_prior_purchase", return_value=False), \
         patch("app.advisor.payment_engine.create_checkout_session", return_value="https://stripe/x") as cs:
        r = c.get("/advisor/campaign/checkout?letters=99", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "https://stripe/x"
    kw = cs.call_args.kwargs
    assert kw["line_items"][0]["price_data"]["unit_amount"] == 50000
    assert kw["service"] == "prospect_letters"
    assert kw["extra_metadata"] == {"letters": "25", "kind": "first_campaign"}


def test_checkout_repeat_is_20_per_letter():
    c = _advisor_client()
    with patch("app.advisor.database.get_user_profile", return_value=ADVISOR_PROFILE), \
         patch("app.advisor.database.prospect_has_prior_purchase", return_value=True), \
         patch("app.advisor.payment_engine.create_checkout_session", return_value="https://stripe/y") as cs:
        c.get("/advisor/campaign/checkout?letters=12", follow_redirects=False)
    kw = cs.call_args.kwargs
    assert kw["line_items"][0]["price_data"]["unit_amount"] == 24000
    assert kw["extra_metadata"]["letters"] == "12" and kw["extra_metadata"]["kind"] == "repeat"


def test_fulfillment_credits_prospect_ledger():
    import payment_engine
    session = MagicMock()
    session.payment_status = "paid"
    session.metadata = {"user_email": "ada@wealth.com", "service": "prospect_letters",
                        "letters": "25", "kind": "first_campaign"}
    session.amount_total = 50000
    with patch("payment_engine.verify_session", return_value=session), \
         patch("database.is_fulfillment_recorded", return_value=False), \
         patch("database.add_prospect_credits", return_value=True) as ledger, \
         patch("database.add_advisor_credit") as legacy, \
         patch("database.record_stripe_fulfillment") as rec, \
         patch("payment_engine.audit_engine.log_event"):
        ok, msg = payment_engine.handle_payment_return("cs_123")
    assert ok and "25" in msg
    ledger.assert_called_once_with("ada@wealth.com", 25, "purchase", "cs_123")
    legacy.assert_not_called()          # did NOT hand out a $99 engagement credit
    rec.assert_called_once()


def test_fulfillment_legacy_path_untouched():
    import payment_engine
    session = MagicMock()
    session.payment_status = "paid"
    session.metadata = {"user_email": "ada@wealth.com", "service": "VerbaPost"}
    session.amount_total = 9900
    with patch("payment_engine.verify_session", return_value=session), \
         patch("database.is_fulfillment_recorded", return_value=False), \
         patch("database.add_prospect_credits") as ledger, \
         patch("database.add_advisor_credit") as legacy, \
         patch("database.record_stripe_fulfillment"), \
         patch("payment_engine.audit_engine.log_event"):
        ok, _ = payment_engine.handle_payment_return("cs_999")
    assert ok
    legacy.assert_called_once_with("ada@wealth.com", 1)
    ledger.assert_not_called()


# ============================================================
# Advisor portal: page setup + CSV send log
# ============================================================

def test_advisor_portal_shows_campaign_section():
    c = _advisor_client()
    with patch("app.advisor.database.get_user_profile", return_value=ADVISOR_PROFILE), \
         patch("app.advisor.database.get_advisor_clients", return_value=[]), \
         patch("app.advisor.database.get_advisor_projects_for_media", return_value=[]), \
         patch("app.advisor.database.get_advisor_page_by_email", return_value=dict(PAGE)), \
         patch("app.advisor.database.prospect_has_prior_purchase", return_value=False), \
         patch("app.advisor.database.prospect_credit_balance", return_value=25), \
         patch("app.advisor.database.list_campaigns", return_value=[]), \
         patch("app.advisor.database.list_prospect_letters", return_value=[]):
        r = c.get("/advisor")
    assert r.status_code == 200
    assert "Prospect Campaign" in r.text
    assert "/a/ada" in r.text
    assert "Start first campaign ($500 · 25 invitations)" in r.text
    assert "/advisor/campaign/export.csv" in r.text
    # the mailing-list uploader is the mass-mail entry point
    assert "/advisor/campaign/upload" in r.text
    assert "Invitations remaining" in r.text


def test_save_campaign_page_validates_slug_and_uploads_photo():
    c = _advisor_client()
    with patch("app.advisor.database.get_user_profile", return_value=ADVISOR_PROFILE), \
         patch("app.advisor.database.get_advisor_clients", return_value=[]), \
         patch("app.advisor.database.get_advisor_projects_for_media", return_value=[]), \
         patch("app.advisor.database.get_advisor_page_by_email", return_value={}), \
         patch("app.advisor.database.prospect_has_prior_purchase", return_value=False), \
         patch("app.advisor.database.prospect_credit_balance", return_value=0), \
         patch("app.advisor.database.list_campaigns", return_value=[]), \
         patch("app.advisor.database.list_prospect_letters", return_value=[]), \
         patch("app.advisor.audit_engine.log_event"), \
         patch("app.advisor.database.upsert_advisor_page", return_value=(True, "Saved")) as up:
        r = c.post("/advisor/campaign/page", data={"slug": "Bad Slug!", "display_name": "Ada"})
        assert "Page address must be" in r.text
        up.assert_not_called()

        # tiny valid PNG (1x1)
        import base64
        png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")
        r = c.post("/advisor/campaign/page",
                   data={"slug": "ada-advisor", "display_name": "Ada Advisor", "firm_name": "Ada Wealth",
                         "return_line1": "9 Money Ln", "return_city": "Nashville",
                         "return_state": "tn", "return_zip": "37203", "active": "on"},
                   files={"photo": ("me.png", png, "image/png")})
        assert r.status_code == 200 and "saved" in r.text.lower()
        kw = up.call_args.kwargs
        assert kw["slug"] == "ada-advisor" and kw["return_state"] == "TN"
        assert kw["photo_mime"] in ("image/jpeg", "image/png") and kw["photo_data"]


def test_csv_export_is_scoped_to_advisor_and_guards_formulas():
    rows = [{"id": 1, "created_at": datetime(2026, 9, 8, 15, 0), "status": "Sent",
             "advisor_email": "ada@wealth.com", "prospect_name": "=HYPERLINK(evil)",
             "prospect_phone": "+16155550142", "recipient_name": "Sam", "recipient_line1": "12 Oak",
             "recipient_city": "Franklin", "recipient_state": "TN", "recipient_zip": "37064",
             "consent_version": "2026-09-v1", "consent_at": datetime(2026, 9, 8, 14, 59),
             "consent_ip": "203.0.113.9", "consent_user_agent": "ua", "consent_text": "I consent…",
             "dnc_status": "internal_only", "dnc_provider": "internal", "dnc_checked_at": None,
             "call_sid": "CA1", "call_attempts": 1, "last_call_at": None, "audio_url": "https://api.twilio.com/x",
             "letter_version": "prospect-v1", "queued_at": None, "sent_at": None,
             "letter_text": "The story.", "transcript_raw": "the story"}]
    c = _advisor_client()
    with patch("app.advisor.database.list_prospect_letters", return_value=rows) as lst, \
         patch("app.advisor.audit_engine.log_event"):
        r = c.get("/advisor/campaign/export.csv")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    lst.assert_called_once_with(advisor_email="ada@wealth.com")
    lines = r.text.strip().splitlines()
    assert lines[0].startswith("id,created_at_utc,status,advisor_email,prospect_name")
    assert "consent_text" in lines[0] and "letter_text" in lines[0]
    assert "'=HYPERLINK(evil)" in lines[1]          # formula-injection guard
    assert "2026-09-08T15:00:00" in lines[1]
    # anonymous -> login
    assert _client().get("/advisor/campaign/export.csv", follow_redirects=False).status_code == 302


# ============================================================
# Admin: print queue, PDFs, mark sent, grant, house CSV
# ============================================================

def _admin_client():
    c = _client()
    with patch("app.auth.auth_engine.sign_in", return_value=(MagicMock(), None)), \
         patch("app.auth.database.get_user_profile", return_value={"role": "user"}), \
         patch.dict(os.environ, {"ADMIN_EMAIL": "boss@verbapost.com"}):
        c.post("/login", data={"email": "boss@verbapost.com", "password": "pw12345678"})
    return c


PROSPECT_ITEM = {
    "kind": "prospect", "id": 42, "who": "Pat -> Sam (gift from Ada Advisor)",
    "content": "When your grandmother and I first met at the lake house...",
    "meta": {"firm_name": "Ada Wealth", "advisor_name": "Ada Advisor", "advisor_email": "ada@wealth.com",
             "storyteller": "Pat Prospect", "heir_name": "Sam Recipient", "prompt": "",
             "date": "September 08, 2026",
             "address": {"line1": "12 Oak St", "city": "Franklin", "state": "TN", "zip": "37064"},
             "return": {"line1": "9 Money Ln", "city": "Nashville", "state": "TN", "zip": "37203"},
             "recipients": []},
}


def test_admin_queue_lists_prospect_letters_from_db():
    from app.admin import load_queue
    row = {"id": 42, "advisor_email": "ada@wealth.com", "prospect_name": "Pat", "recipient_name": "Sam",
           "letter_text": "Story", "transcript_raw": "story", "created_at": datetime(2026, 9, 8),
           "recipient_line1": "12 Oak", "recipient_city": "Franklin", "recipient_state": "TN", "recipient_zip": "37064"}
    with patch("app.admin.database.get_db_session", side_effect=ConnectionError("no db")), \
         patch("app.admin.database.list_prospect_letters", return_value=[row]) as lst, \
         patch("app.admin.database.get_advisor_page_by_email", return_value=dict(PAGE)):
        items = load_queue()
    lst.assert_called_once_with(statuses=["Approved"])
    assert len(items) == 1 and items[0]["kind"] == "prospect"
    assert items[0]["meta"]["advisor_name"] == "Ada Advisor"
    assert items[0]["meta"]["return"]["line1"] == "9 Money Ln"


def test_admin_prospect_pdfs_and_mark_sent_and_grant():
    c = _admin_client()
    with patch("app.admin.load_queue", return_value=[PROSPECT_ITEM]), \
         patch("app.admin.health_report", return_value=[]):
        r = c.get("/admin")
        assert r.status_code == 200 and "Prospect gift letter" in r.text
        assert "Return address on envelope: <strong>Ada Advisor</strong>" in r.text
        with patch("app.admin.letter_format.create_pdf", return_value=b"%PDF-letter") as pdf:
            r = c.get("/admin/letter/prospect/42.pdf")
            assert r.status_code == 200 and r.content == b"%PDF-letter"
            kw = pdf.call_args.kwargs
            assert kw["audio_url"] == "p42"                 # QR -> /play/p42
            assert kw["compliments_of"] == "Ada Advisor, Ada Wealth"
            assert kw["recipient_name"] == "Sam Recipient"
        with patch("app.admin.envelope_format.create_envelope", return_value=b"%PDF-env") as env:
            r = c.get("/admin/envelope/prospect/42.pdf")
            assert r.status_code == 200
            to_obj, from_obj = env.call_args[0]
            assert to_obj["name"] == "Sam Recipient" and to_obj["zip_code"] == "37064"
            assert from_obj["name"].startswith("Ada Advisor") and "Ada Wealth" in from_obj["name"]
            assert from_obj["address_line1"] == "9 Money Ln"
    with patch("app.admin.database.update_prospect_letter") as upd, \
         patch("app.admin.audit_engine.log_event"):
        r = c.post("/admin/queue/prospect/42/sent", follow_redirects=False)
    assert r.status_code == 303
    assert upd.call_args.kwargs["status"] == "Sent" and upd.call_args.kwargs["sent_at"]
    with patch("app.admin.database.add_prospect_credits", return_value=True) as grant, \
         patch("app.admin.audit_engine.log_event"):
        r = c.post("/admin/prospect/grant", data={"email": "ada@wealth.com", "amount": "25", "note": "inv 7"},
                   follow_redirects=False)
    assert r.status_code == 303 and "Granted+25" in r.headers["location"]
    assert grant.call_args[0][:3] == ("ada@wealth.com", 25, "grant")


def test_admin_house_csv_exports_all_advisors():
    c = _admin_client()
    with patch("app.admin.database.list_prospect_letters", return_value=[]) as lst:
        r = c.get("/admin/prospect/export.csv")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    lst.assert_called_once_with()


# ============================================================
# Real PDF rendering (no mocks) — the letter must build with the new labels
# ============================================================

def test_letter_pdf_renders_gift_labels_for_real():
    import letter_format
    pdf = letter_format.create_pdf(
        body_text="When your grandmother and I first met at the lake house in 1971, it rained for a week.",
        to_addr={}, from_addr={"name": "Pat Prospect"}, advisor_firm="Ada Wealth",
        audio_url="p42", question_text="Tell them about a memory.",
        compliments_of="Ada Advisor, Ada Wealth", recipient_name="Sam Recipient")
    assert pdf[:4] == b"%PDF" and len(pdf) > 1500
    import envelope_format
    env = envelope_format.create_envelope(
        {"name": "Sam Recipient", "address_line1": "12 Oak St", "city": "Franklin", "state": "TN", "zip_code": "37064"},
        {"name": "Ada Advisor\nAda Wealth", "address_line1": "9 Money Ln", "city": "Nashville", "state": "TN", "zip_code": "37203"})
    assert env[:4] == b"%PDF"


def test_prospect_call_script_escapes_and_discloses_recording():
    import ai_engine
    fake_client = MagicMock()
    fake_client.calls.create.return_value.sid = "CA777"
    with patch("ai_engine.get_secret", side_effect=lambda k: {"twilio.account_sid": "AC", "twilio.auth_token": "T",
                                                               "twilio.from_number": "+16155550000",
                                                               "WEBHOOK_BASE_URL": "https://staging.verbapost.com"}.get(k)), \
         patch("twilio.rest.Client", return_value=fake_client):
        sid, err = ai_engine.trigger_prospect_call(
            to_phone="+16155550142", prospect_name="Pat Prospect", advisor_name="Ada Advisor",
            firm_name="Ada Wealth", recipient_name="Sam <Dial>+1900</Dial>", question_text=None)
    assert sid == "CA777" and err is None
    kw = fake_client.calls.create.call_args.kwargs
    assert kw["to"] == "+16155550142" and kw["timeout"] == ai_engine.PROSPECT_CALL_TIMEOUT_SECONDS
    twiml = kw["twiml"]
    assert "<Dial>" not in twiml and "&lt;Dial&gt;" in twiml        # injection neutralized
    assert "This call is being recorded" in twiml
    assert "on behalf of Ada Advisor at Ada Wealth" in twiml
    assert 'recordingStatusCallback="https://staging.verbapost.com/webhooks/twilio/recording"' in twiml
