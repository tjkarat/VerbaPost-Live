"""
Phase 4 regression tests: admin console (auth gate, queue, credits, PDFs).
Run:  python -m pytest tests/test_phase4_admin.py -v
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


def _admin_client():
    c = TestClient(app, base_url="https://testserver")
    with patch("app.auth.auth_engine.sign_in", return_value=(MagicMock(), None)), \
         patch("app.auth.database.get_user_profile", return_value={"role": "user"}), \
         patch.dict(os.environ, {"ADMIN_EMAIL": "boss@verbapost.com"}):
        c.post("/login", data={"email": "boss@verbapost.com", "password": "pw12345678"})
    return c


QUEUE_ITEM = {
    "kind": "heirloom", "id": 9, "who": "Harry (via ada@wealth.com)",
    "content": "Once upon a time in Nashville...",
    "meta": {"firm_name": "Ada Wealth", "storyteller": "Grandma Rose",
             "heir_name": "Harry", "heir_email": "harry@x.com",
             "prompt": "Tell me about your mother.", "date": "July 7, 2026",
             "address": {"line1": "1 Main St", "city": "Nashville", "state": "TN", "zip": "37201"},
             "recipients": [{"name": "Bro", "street": "2 Oak", "city": "Austin",
                             "state": "TX", "zip_code": "78701"}]},
}


def test_admin_requires_admin_role():
    # anonymous
    assert client.get("/admin", follow_redirects=False).status_code == 302
    # ordinary logged-in user
    c = TestClient(app, base_url="https://testserver")
    with patch("app.auth.auth_engine.sign_in", return_value=(MagicMock(), None)), \
         patch("app.auth.database.get_user_profile", return_value={"role": "advisor"}):
        c.post("/login", data={"email": "adv@x.com", "password": "pw12345678"})
    r = c.get("/admin", follow_redirects=False)
    assert r.status_code == 302  # advisors are not admins


def test_admin_dashboard_renders_queue_with_all_recipients():
    c = _admin_client()
    with patch("app.admin.load_queue", return_value=[QUEUE_ITEM]), \
         patch("app.admin.health_report", return_value=[("ok", "Database", "Connected")]):
        r = c.get("/admin")
    assert r.status_code == 200
    assert "Once upon a time" in r.text
    assert "Mail 2 cop" in r.text          # heir + 1 recipient
    assert "Bro" in r.text                  # extra recipient listed
    assert "recipient=0" in r.text          # per-recipient envelope link


def test_letter_pdf_streams_for_admin():
    c = _admin_client()
    with patch("app.admin._queue_item", return_value=QUEUE_ITEM), \
         patch("app.admin.letter_format.create_pdf", return_value=b"%PDF-fake"):
        r = c.get("/admin/letter/heirloom/9.pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content == b"%PDF-fake"


def test_envelope_pdf_for_extra_recipient_uses_their_address():
    c = _admin_client()
    with patch("app.admin._queue_item", return_value=QUEUE_ITEM), \
         patch("app.admin.database.get_user_profile", return_value={}), \
         patch("app.admin.envelope_format.create_envelope",
               return_value=b"%PDF-env") as mock_env:
        r = c.get("/admin/envelope/heirloom/9.pdf?recipient=0")
    assert r.status_code == 200
    to_obj = mock_env.call_args[0][0]
    assert to_obj["name"] == "Bro"
    assert to_obj["city"] == "Austin"


def test_mark_sent_updates_and_redirects():
    c = _admin_client()
    fake_session = MagicMock()
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=fake_session)
    ctx.__exit__ = MagicMock(return_value=False)
    with patch("app.admin.database.get_db_session", return_value=ctx), \
         patch("app.admin.audit_engine.log_event"):
        r = c.post("/admin/queue/heirloom/9/sent", follow_redirects=False)
    assert r.status_code == 303
    assert fake_session.execute.called


def test_credit_grant_requires_admin():
    r = client.post("/admin/credits", data={"email": "x@y.com", "amount": 1},
                    follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/login"
