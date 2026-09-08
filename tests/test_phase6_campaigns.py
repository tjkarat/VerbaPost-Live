"""
Phase 6 regression tests: invitation campaigns (the mass-mail side).

CSV parsing, draft creation, proof PDF, PostGrid send with financial
atomicity, personal-link landing + attribution, per-mailing CSV, and the
re-pointed pricing (invitations are the billable unit).

Run: python -m pytest tests/test_phase6_campaigns.py -v
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("ENV", "staging")
os.environ.setdefault("BASE_URL", "https://staging.verbapost.com")

from fastapi.testclient import TestClient  # noqa: E402

import campaign_engine  # noqa: E402
import invitation_format  # noqa: E402
import pricing_engine  # noqa: E402
from app.main import app  # noqa: E402

PAGE = {"id": 1, "advisor_email": "ada@wealth.com", "slug": "ada", "display_name": "Ada Advisor",
        "firm_name": "Ada Wealth", "disclosure": "Securities via Example LLC.", "invite_body": None,
        "return_line1": "9 Money Ln", "return_city": "Nashville", "return_state": "TN",
        "return_zip": "37203", "active": True, "prompt": None, "headline": None, "intro": None,
        "photo_data": None, "photo_mime": None}

ADVISOR_PROFILE = {"role": "advisor", "full_name": "Ada Advisor",
                   "advisor_firm": "Ada Wealth", "credits": 0}

GOOD_CSV = (
    b"First Name,Last Name,Street Address,City,State,Zip\n"
    b"Margaret,Wilson,12 Oak Street,Franklin,Tennessee,37064\n"
    b"Harold,Yeats,88 Elm Ave Apt 3,Nashville,TN,37203-1122\n"
)


def _client():
    return TestClient(app, base_url="https://testserver")


def _advisor_client():
    c = _client()
    with patch("app.auth.auth_engine.sign_in", return_value=(MagicMock(), None)), \
         patch("app.auth.database.get_user_profile", return_value=ADVISOR_PROFILE):
        c.post("/login", data={"email": "ada@wealth.com", "password": "pw12345678"})
    return c


def _portal_patches():
    """Everything /advisor renders, so _render() works without a database."""
    return [
        patch("app.advisor.database.get_user_profile", return_value=ADVISOR_PROFILE),
        patch("app.advisor.database.get_advisor_clients", return_value=[]),
        patch("app.advisor.database.get_advisor_projects_for_media", return_value=[]),
        patch("app.advisor.database.prospect_has_prior_purchase", return_value=True),
        patch("app.advisor.database.prospect_credit_balance", return_value=25),
        patch("app.advisor.database.list_campaigns", return_value=[]),
        patch("app.advisor.database.list_prospect_letters", return_value=[]),
    ]


class _Stack:
    def __init__(self, patches):
        self.patches = patches

    def __enter__(self):
        for p in self.patches:
            p.__enter__()
        return self

    def __exit__(self, *a):
        for p in reversed(self.patches):
            p.__exit__(*a)


# ============================================================
# CSV parsing
# ============================================================

def test_parse_maps_common_headers_and_normalizes():
    rows, problems, mapping = campaign_engine.parse_mailing_list(GOOD_CSV)
    assert len(rows) == 2 and not problems
    assert mapping["line1"] == "Street Address" and mapping["zip_code"] == "Zip"
    assert rows[0] == {"full_name": "Margaret Wilson", "first_name": "Margaret",
                       "line1": "12 Oak Street", "line2": None, "city": "Franklin",
                       "state": "TN", "zip_code": "37064"}          # full state name -> code
    assert rows[1]["zip_code"] == "37203-1122"                       # ZIP+4 preserved


def test_parse_accepts_single_name_column_and_alternate_headers():
    csv_bytes = b"Name,Address,City,ST,Postal Code\nRuth Bader,1 Court St,Nashville,tn,37201\n"
    rows, problems, _ = campaign_engine.parse_mailing_list(csv_bytes)
    assert not problems
    assert rows[0]["full_name"] == "Ruth Bader" and rows[0]["first_name"] == "Ruth"
    assert rows[0]["state"] == "TN"


def test_parse_recovers_excel_stripped_leading_zero_zip():
    csv_bytes = b"Name,Address,City,State,Zip\nPaul Revere,1 Beacon St,Boston,MA,2134\n"
    rows, _, _ = campaign_engine.parse_mailing_list(csv_bytes)
    assert rows[0]["zip_code"] == "02134"


def test_parse_reports_bad_rows_without_dropping_the_file():
    csv_bytes = (b"Name,Address,City,State,Zip\n"
                 b"Good Person,1 Main St,Franklin,TN,37064\n"
                 b",2 Main St,Franklin,TN,37064\n"                 # no name
                 b"No Street,,Franklin,TN,37064\n"                 # no street
                 b"Bad State,3 Main St,Franklin,Freedonia,37064\n"  # unknown state
                 b"Bad Zip,4 Main St,Franklin,TN,abc\n"            # bad zip
                 b"Good Person,1 Main St,Franklin,TN,37064\n")     # exact duplicate
    rows, problems, _ = campaign_engine.parse_mailing_list(csv_bytes)
    assert len(rows) == 1
    reasons = " ".join(r for _, r in problems)
    assert "missing name" in reasons and "missing street" in reasons
    assert "unrecognized state" in reasons and "bad ZIP" in reasons and "duplicate" in reasons


def test_parse_rejects_file_without_required_headers():
    rows, problems, _ = campaign_engine.parse_mailing_list(b"Email,Phone\na@b.com,6155550142\n")
    assert not rows and "Couldn't find" in problems[0][1]


def test_parse_handles_empty_file_and_bom():
    rows, problems, _ = campaign_engine.parse_mailing_list(b"")
    assert not rows and problems
    bom = b"\xef\xbb\xbfName,Address,City,State,Zip\nA Person,1 St,Franklin,TN,37064\n"
    rows, problems, _ = campaign_engine.parse_mailing_list(bom)
    assert len(rows) == 1 and not problems


def test_parse_caps_row_count():
    header = b"Name,Address,City,State,Zip\n"
    body = b"".join(f"P{i},{i} Main St,Franklin,TN,37064\n".encode()
                    for i in range(campaign_engine.MAX_ROWS_PER_UPLOAD + 20))
    rows, problems, _ = campaign_engine.parse_mailing_list(header + body)
    assert len(rows) == campaign_engine.MAX_ROWS_PER_UPLOAD
    assert any("Stopped at" in r for _, r in problems)


# ============================================================
# Invitation PDF
# ============================================================

def test_invitation_pdf_renders_with_personal_link():
    pdf = invitation_format.create_invitation_pdf(
        first_name="Margaret", personal_url="https://app.verbapost.com/a/ada/i/Tok123",
        advisor_name="Ada Advisor", firm_name="Ada Wealth",
        disclosure="Securities via Example LLC.")
    assert pdf[:4] == b"%PDF" and len(pdf) > 2000
    # Body must clear PostGrid's address window (AI_RULES.md: y=115mm)
    assert invitation_format.BODY_START_Y >= 115.0


def test_invitation_pdf_uses_advisor_custom_body():
    page = dict(PAGE, invite_body="A completely custom note from me to you.")
    inv = {"token": "Tok123", "first_name": "Margaret", "full_name": "Margaret Wilson"}
    with patch("campaign_engine.invitation_format.create_invitation_pdf",
               return_value=b"%PDF-x") as make:
        campaign_engine.build_invitation_pdf(page, inv, "https://staging.verbapost.com")
    kw = make.call_args.kwargs
    assert kw["body"] == "A completely custom note from me to you."
    assert kw["personal_url"] == "https://staging.verbapost.com/a/ada/i/Tok123"
    assert kw["first_name"] == "Margaret"


def test_invitation_pdf_returns_none_instead_of_raising():
    with patch("invitation_format.qrcode.make", side_effect=RuntimeError("boom")):
        assert invitation_format.create_invitation_pdf("A", "u", "Ada") is None


# ============================================================
# Sending — PostGrid + financial atomicity
# ============================================================

CAMP = {"id": 5, "advisor_email": "ada@wealth.com", "name": "Fall list", "status": "draft",
        "total_rows": 2}
INV1 = {"id": 11, "campaign_id": 5, "advisor_email": "ada@wealth.com", "token": "Tok1",
        "full_name": "Margaret Wilson", "first_name": "Margaret", "line1": "12 Oak St",
        "line2": None, "city": "Franklin", "state": "TN", "zip_code": "37064", "status": "pending"}
INV2 = dict(INV1, id=12, token="Tok2", full_name="Harold Yeats", first_name="Harold",
            line1="88 Elm Ave", city="Nashville", zip_code="37203")


def test_send_campaign_mails_each_row_and_consumes_one_credit_each():
    updates, ledger = [], []
    with patch("campaign_engine.database.get_campaign", return_value=dict(CAMP)), \
         patch("campaign_engine.database.get_advisor_page_by_email", return_value=dict(PAGE)), \
         patch("campaign_engine.database.update_campaign") as upd_camp, \
         patch("campaign_engine.database.list_invitations",
               side_effect=[[dict(INV1), dict(INV2)],
                            [dict(INV1, status="sent"), dict(INV2, status="sent")]]), \
         patch("campaign_engine.database.prospect_credit_balance", return_value=25), \
         patch("campaign_engine.database.update_invitation",
               side_effect=lambda i, **k: updates.append((i, k))), \
         patch("campaign_engine.database.add_prospect_credits",
               side_effect=lambda *a, **k: ledger.append(a)), \
         patch("campaign_engine.database.log_event"), \
         patch("campaign_engine.invitation_format.create_invitation_pdf", return_value=b"%PDF-x"), \
         patch("campaign_engine.mailer.is_test_mode", return_value=False), \
         patch("campaign_engine.mailer.send_invitation_letter",
               side_effect=[("pg_1", None), ("pg_2", None)]) as send:
        sent, failed, skipped = campaign_engine.send_campaign(5, "https://staging.verbapost.com")

    assert (sent, failed, skipped) == (2, 0, 0)
    # each letter addressed to its own person, from the advisor
    to1, from1 = send.call_args_list[0][0][1], send.call_args_list[0][0][2]
    assert to1["name"] == "Margaret Wilson" and to1["zip"] == "37064"
    assert from1["name"] == "Ada Advisor" and from1["company"] == "Ada Wealth"
    assert from1["line1"] == "9 Money Ln"
    # idempotency keys are per-row, so a retry can never double-print
    keys = [c.kwargs["idempotency_key"] for c in send.call_args_list]
    assert keys == ["invite:11", "invite:12"]
    # ledger consumed once per accepted letter, never more
    assert ledger == [("ada@wealth.com", -1, "consume", "invite:11"),
                      ("ada@wealth.com", -1, "consume", "invite:12")]
    statuses = [k.get("status") for _, k in updates]
    assert statuses == ["sent", "sent"]
    assert upd_camp.call_args.kwargs["status"] == "sent"


def test_send_campaign_failed_row_costs_nothing():
    with patch("campaign_engine.database.get_campaign", return_value=dict(CAMP)), \
         patch("campaign_engine.database.get_advisor_page_by_email", return_value=dict(PAGE)), \
         patch("campaign_engine.database.update_campaign") as upd_camp, \
         patch("campaign_engine.database.list_invitations",
               side_effect=[[dict(INV1), dict(INV2)],
                            [dict(INV1, status="sent"), dict(INV2, status="failed")]]), \
         patch("campaign_engine.database.prospect_credit_balance", return_value=25), \
         patch("campaign_engine.database.update_invitation") as upd_inv, \
         patch("campaign_engine.database.add_prospect_credits") as ledger, \
         patch("campaign_engine.database.log_event"), \
         patch("campaign_engine.invitation_format.create_invitation_pdf", return_value=b"%PDF-x"), \
         patch("campaign_engine.mailer.is_test_mode", return_value=False), \
         patch("campaign_engine.mailer.send_invitation_letter",
               side_effect=[("pg_1", None), (None, "422: undeliverable address")]):
        sent, failed, skipped = campaign_engine.send_campaign(5, "https://x")

    assert (sent, failed, skipped) == (1, 1, 0)
    assert ledger.call_count == 1                       # only the accepted letter billed
    fail_kw = upd_inv.call_args_list[-1].kwargs
    assert fail_kw["status"] == "failed" and "undeliverable" in fail_kw["error"]
    assert upd_camp.call_args.kwargs["status"] == "partial"


def test_send_campaign_stops_at_zero_balance_and_marks_skipped():
    balances = iter([1, 0])
    with patch("campaign_engine.database.get_campaign", return_value=dict(CAMP)), \
         patch("campaign_engine.database.get_advisor_page_by_email", return_value=dict(PAGE)), \
         patch("campaign_engine.database.update_campaign"), \
         patch("campaign_engine.database.list_invitations",
               side_effect=[[dict(INV1), dict(INV2)],
                            [dict(INV1, status="sent"), dict(INV2, status="skipped")]]), \
         patch("campaign_engine.database.prospect_credit_balance",
               side_effect=lambda _e: next(balances)), \
         patch("campaign_engine.database.update_invitation") as upd_inv, \
         patch("campaign_engine.database.add_prospect_credits"), \
         patch("campaign_engine.database.log_event"), \
         patch("campaign_engine.invitation_format.create_invitation_pdf", return_value=b"%PDF-x"), \
         patch("campaign_engine.mailer.is_test_mode", return_value=False), \
         patch("campaign_engine.mailer.send_invitation_letter",
               return_value=("pg_1", None)) as send:
        sent, failed, skipped = campaign_engine.send_campaign(5, "https://x")

    assert (sent, failed, skipped) == (1, 0, 1)
    assert send.call_count == 1                          # never dialed PostGrid without a credit
    assert upd_inv.call_args_list[-1].kwargs["skip_reason"] == "no invitations remaining"


def test_send_campaign_refuses_without_a_page():
    with patch("campaign_engine.database.get_campaign", return_value=dict(CAMP)), \
         patch("campaign_engine.database.get_advisor_page_by_email", return_value={}), \
         patch("campaign_engine.database.update_campaign") as upd, \
         patch("campaign_engine.mailer.send_invitation_letter") as send:
        assert campaign_engine.send_campaign(5, "https://x") == (0, 0, 0)
    send.assert_not_called()
    assert upd.call_args.kwargs["status"] == "failed"


def test_mailer_send_invitation_posts_expected_postgrid_fields():
    import mailer
    resp = MagicMock(status_code=201)
    resp.json.return_value = {"id": "letter_abc"}
    with patch("mailer.get_api_key", return_value="live_sk_x"), \
         patch("mailer.requests.post", return_value=resp) as post:
        pg_id, err = mailer.send_invitation_letter(
            b"%PDF-x", {"name": "Margaret Wilson", "line1": "12 Oak St", "city": "Franklin",
                        "state": "TN", "zip": "37064"},
            {"name": "Ada Advisor", "company": "Ada Wealth", "line1": "9 Money Ln",
             "city": "Nashville", "state": "TN", "zip": "37203"},
            description="test", idempotency_key="invite:11")
    assert pg_id == "letter_abc" and err is None
    data = post.call_args.kwargs["data"]
    assert data["to[firstName]"] == "Margaret" and data["to[lastName]"] == "Wilson"
    assert data["from[companyName]"] == "Ada Wealth"
    assert data["addressPlacement"] == "top_first_page"    # our PDF leaves 115mm clear
    assert post.call_args.kwargs["headers"]["Idempotency-Key"] == "invite:11"


def test_mailer_reports_error_text_instead_of_raising():
    import mailer
    resp = MagicMock(status_code=422, text='{"error": {"message": "invalid address"}}')
    resp.json.return_value = {"error": {"message": "invalid address"}}
    with patch("mailer.get_api_key", return_value="live_sk_x"), \
         patch("mailer.requests.post", return_value=resp):
        pg_id, err = mailer.send_invitation_letter(b"x", {}, {}, "d", "k")
    assert pg_id is None and "invalid address" in err
    with patch("mailer.get_api_key", return_value=None):
        pg_id, err = mailer.send_invitation_letter(b"x", {}, {}, "d", "k")
    assert pg_id is None and "POSTGRID_API_KEY" in err


def test_mailer_test_mode_detection():
    import mailer
    with patch("mailer.get_api_key", return_value="test_sk_123"):
        assert mailer.is_test_mode()
    with patch("mailer.get_api_key", return_value="live_sk_123"):
        assert not mailer.is_test_mode()


# ============================================================
# Advisor portal: upload -> review -> proof -> send
# ============================================================

def test_upload_requires_page_and_return_address():
    c = _advisor_client()
    with _Stack(_portal_patches()), \
         patch("app.advisor.database.get_advisor_page_by_email", return_value=None):
        r = c.post("/advisor/campaign/upload", files={"mailing_list": ("l.csv", GOOD_CSV, "text/csv")})
    assert "Set up your prospect page first" in r.text
    no_addr = dict(PAGE, return_line1=None)
    with _Stack(_portal_patches()), \
         patch("app.advisor.database.get_advisor_page_by_email", return_value=no_addr):
        r = c.post("/advisor/campaign/upload", files={"mailing_list": ("l.csv", GOOD_CSV, "text/csv")})
    assert "return address" in r.text


def test_upload_creates_draft_and_shows_review():
    c = _advisor_client()
    rows = [dict(INV1), dict(INV2)]
    with _Stack(_portal_patches()), \
         patch("app.advisor.database.get_advisor_page_by_email", return_value=dict(PAGE)), \
         patch("app.advisor.database.previously_mailed_addresses", return_value=set()), \
         patch("app.advisor.database.create_campaign", return_value=5) as create, \
         patch("app.advisor.database.get_campaign", return_value=dict(CAMP)), \
         patch("app.advisor.database.list_invitations", return_value=rows), \
         patch("app.advisor.audit_engine.log_event"):
        r = c.post("/advisor/campaign/upload",
                   data={"list_name": "Fall list"},
                   files={"mailing_list": ("list.csv", GOOD_CSV, "text/csv")})
    assert r.status_code == 200
    assert "Loaded 2 addresses" in r.text
    assert "Margaret Wilson" in r.text and "Harold Yeats" in r.text
    assert "Preview the letter" in r.text and "Send 2 invitations" in r.text
    passed_rows = create.call_args[0][3]
    assert len(passed_rows) == 2 and passed_rows[0]["state"] == "TN"


def test_upload_drops_addresses_already_mailed():
    c = _advisor_client()
    already = {("12 oak street", "37064")}
    with _Stack(_portal_patches()), \
         patch("app.advisor.database.get_advisor_page_by_email", return_value=dict(PAGE)), \
         patch("app.advisor.database.previously_mailed_addresses", return_value=already), \
         patch("app.advisor.database.create_campaign", return_value=6) as create, \
         patch("app.advisor.database.get_campaign", return_value=dict(CAMP, id=6, total_rows=1)), \
         patch("app.advisor.database.list_invitations", return_value=[dict(INV2)]), \
         patch("app.advisor.audit_engine.log_event"):
        r = c.post("/advisor/campaign/upload", files={"mailing_list": ("l.csv", GOOD_CSV, "text/csv")})
    assert "1 skipped (already mailed)" in r.text
    assert len(create.call_args[0][3]) == 1


def test_upload_rejects_unusable_file():
    c = _advisor_client()
    with _Stack(_portal_patches()), \
         patch("app.advisor.database.get_advisor_page_by_email", return_value=dict(PAGE)), \
         patch("app.advisor.database.create_campaign") as create:
        r = c.post("/advisor/campaign/upload",
                   files={"mailing_list": ("l.csv", b"Email\na@b.com\n", "text/csv")})
    assert "read that list" in r.text and "Email" not in r.text.split("msg-error")[1][:200]
    create.assert_not_called()


def test_proof_pdf_uses_the_first_row():
    c = _advisor_client()
    with patch("app.advisor.database.get_user_profile", return_value=ADVISOR_PROFILE), \
         patch("app.advisor.database.get_campaign", return_value=dict(CAMP)), \
         patch("app.advisor.database.list_invitations", return_value=[dict(INV1), dict(INV2)]), \
         patch("app.advisor.database.get_advisor_page_by_email", return_value=dict(PAGE)), \
         patch("app.advisor.campaign_engine.build_invitation_pdf",
               return_value=b"%PDF-proof") as build:
        r = c.get("/advisor/campaign/5/proof.pdf")
    assert r.status_code == 200 and r.content == b"%PDF-proof"
    assert r.headers["content-type"] == "application/pdf"
    assert build.call_args[0][1]["id"] == 11


def test_proof_and_rows_reject_another_advisors_campaign():
    c = _advisor_client()
    with patch("app.advisor.database.get_user_profile", return_value=ADVISOR_PROFILE), \
         patch("app.advisor.database.get_campaign", return_value=None) as get:
        assert c.get("/advisor/campaign/99/proof.pdf").status_code == 404
        assert c.get("/advisor/campaign/99/rows.csv").status_code == 404
    # ownership is enforced in the query, not in the template
    assert get.call_args[0][1] == "ada@wealth.com"


def test_send_queues_background_task_and_warns_on_short_balance():
    c = _advisor_client()
    pend = [dict(INV1), dict(INV2), dict(INV1, id=13, token="Tok3")]
    with _Stack(_portal_patches()), \
         patch("app.advisor.database.get_advisor_page_by_email", return_value=dict(PAGE)), \
         patch("app.advisor.database.get_campaign", return_value=dict(CAMP)), \
         patch("app.advisor.database.list_invitations", return_value=pend), \
         patch("app.advisor.database.prospect_credit_balance", return_value=2), \
         patch("app.advisor.database.update_invitation"), \
         patch("app.advisor.audit_engine.log_event"), \
         patch("app.advisor.mailer.is_test_mode", return_value=False), \
         patch("app.advisor.campaign_engine.send_campaign", return_value=(2, 0, 1)) as send:
        r = c.post("/advisor/campaign/5/send")
    assert r.status_code == 200
    assert "Sending 2 invitation(s)" in r.text
    assert "1 will wait until you buy more" in r.text
    send.assert_called_once()
    assert send.call_args[0][0] == 5


def test_send_refuses_with_no_balance_and_flags_test_mode():
    c = _advisor_client()
    with _Stack(_portal_patches()), \
         patch("app.advisor.database.get_advisor_page_by_email", return_value=dict(PAGE)), \
         patch("app.advisor.database.get_campaign", return_value=dict(CAMP)), \
         patch("app.advisor.database.list_invitations", return_value=[dict(INV1)]), \
         patch("app.advisor.database.prospect_credit_balance", return_value=0), \
         patch("app.advisor.campaign_engine.send_campaign") as send:
        r = c.post("/advisor/campaign/5/send")
    assert "no invitations remaining" in r.text
    send.assert_not_called()

    with _Stack(_portal_patches()), \
         patch("app.advisor.database.get_advisor_page_by_email", return_value=dict(PAGE)), \
         patch("app.advisor.database.get_campaign", return_value=dict(CAMP)), \
         patch("app.advisor.database.list_invitations", return_value=[dict(INV1)]), \
         patch("app.advisor.database.prospect_credit_balance", return_value=5), \
         patch("app.advisor.database.update_invitation"), \
         patch("app.advisor.audit_engine.log_event"), \
         patch("app.advisor.mailer.is_test_mode", return_value=True), \
         patch("app.advisor.campaign_engine.send_campaign"):
        r = c.post("/advisor/campaign/5/send")
    assert "TEST MODE" in r.text


def test_per_mailing_csv_lists_status_and_responses():
    c = _advisor_client()
    rows = [dict(INV1, status="sent", postgrid_id="pg_1", sent_at=datetime(2026, 9, 8, 10, 0),
                 responded_letter_id=42, responded_at=datetime(2026, 9, 9, 8, 30)),
            dict(INV2, status="failed", error="bad address")]
    with patch("app.advisor.database.get_user_profile", return_value=ADVISOR_PROFILE), \
         patch("app.advisor.database.get_campaign", return_value=dict(CAMP)), \
         patch("app.advisor.database.list_invitations", return_value=rows):
        r = c.get("/advisor/campaign/5/rows.csv")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    lines = r.text.strip().splitlines()
    assert lines[0].startswith("id,full_name,")
    assert "responded_letter_id" in lines[0]
    assert "pg_1" in lines[1] and "42" in lines[1]
    assert "bad address" in lines[2]


# ============================================================
# The personal link: /a/{slug}/i/{token}
# ============================================================

INVITE_ROW = {"id": 11, "campaign_id": 5, "advisor_email": "ada@wealth.com", "token": "Tok1",
              "full_name": "Margaret Wilson", "first_name": "Margaret", "status": "sent"}


def test_personal_link_greets_by_name_and_prefills():
    with patch("app.prospect.database.get_advisor_page_by_slug", return_value=dict(PAGE)), \
         patch("app.prospect.database.prospect_letters_available", return_value=25), \
         patch("app.prospect.database.get_invitation_by_token", return_value=dict(INVITE_ROW)):
        r = _client().get("/a/ada/i/Tok1")
    assert r.status_code == 200
    assert "Margaret, this is the letter Ada Advisor mailed you." in r.text
    assert 'name="invite_token" value="Tok1"' in r.text
    assert 'value="Margaret Wilson"' in r.text


def test_unknown_or_foreign_token_falls_back_to_plain_page():
    with patch("app.prospect.database.get_advisor_page_by_slug", return_value=dict(PAGE)), \
         patch("app.prospect.database.get_invitation_by_token", return_value=None):
        r = _client().get("/a/ada/i/nope", follow_redirects=False)
    assert r.status_code == 302 and r.headers["location"] == "/a/ada"
    foreign = dict(INVITE_ROW, advisor_email="someone@else.com")
    with patch("app.prospect.database.get_advisor_page_by_slug", return_value=dict(PAGE)), \
         patch("app.prospect.database.get_invitation_by_token", return_value=foreign):
        r = _client().get("/a/ada/i/Tok1", follow_redirects=False)
    assert r.status_code == 302


def test_intake_from_invitation_records_attribution():
    import dnc_engine
    form = {"prospect_name": "Margaret Wilson", "phone": "(615) 555-0142",
            "recipient_name": "Sam Recipient", "line1": "12 Oak St", "city": "Franklin",
            "state": "tn", "zip_code": "37064", "consent": "yes",
            "consent_version": dnc_engine.CONSENT_VERSION, "website": "",
            "invite_token": "Tok1"}
    with patch("app.prospect.database.get_advisor_page_by_slug", return_value=dict(PAGE)), \
         patch("app.prospect.database.prospect_letters_available", return_value=25), \
         patch("app.prospect.database.find_recent_prospect_by_phone", return_value=None), \
         patch("app.prospect.database.get_invitation_by_token", return_value=dict(INVITE_ROW)), \
         patch("app.prospect.database.create_prospect_letter", return_value=42) as create, \
         patch("app.prospect.database.mark_invitation_responded") as responded, \
         patch("app.prospect.database.update_prospect_letter"), \
         patch("app.prospect.database.get_prospect_letter", return_value={"call_attempts": 0}), \
         patch("app.prospect.dnc_engine.scrub",
               return_value={"status": "internal_only", "provider": "internal",
                             "checked_at": datetime.utcnow()}), \
         patch("app.prospect.ai_engine.trigger_prospect_call", return_value=("CA1", None)), \
         patch("app.prospect.audit_engine.log_event"):
        r = _client().post("/a/ada", data=form, follow_redirects=False)
    assert r.status_code == 303
    assert create.call_args.kwargs["invitation_id"] == 11
    responded.assert_called_once_with(11, 42)


def test_intake_ignores_a_token_belonging_to_another_advisor():
    import dnc_engine
    form = {"prospect_name": "Margaret Wilson", "phone": "(615) 555-0143",
            "recipient_name": "Sam", "line1": "12 Oak St", "city": "Franklin",
            "state": "tn", "zip_code": "37064", "consent": "yes",
            "consent_version": dnc_engine.CONSENT_VERSION, "website": "",
            "invite_token": "Tok1"}
    foreign = dict(INVITE_ROW, advisor_email="someone@else.com")
    with patch("app.prospect.database.get_advisor_page_by_slug", return_value=dict(PAGE)), \
         patch("app.prospect.database.prospect_letters_available", return_value=25), \
         patch("app.prospect.database.find_recent_prospect_by_phone", return_value=None), \
         patch("app.prospect.database.get_invitation_by_token", return_value=foreign), \
         patch("app.prospect.database.create_prospect_letter", return_value=43) as create, \
         patch("app.prospect.database.mark_invitation_responded") as responded, \
         patch("app.prospect.database.update_prospect_letter"), \
         patch("app.prospect.database.get_prospect_letter", return_value={"call_attempts": 0}), \
         patch("app.prospect.dnc_engine.scrub",
               return_value={"status": "internal_only", "provider": "internal",
                             "checked_at": datetime.utcnow()}), \
         patch("app.prospect.ai_engine.trigger_prospect_call", return_value=("CA1", None)), \
         patch("app.prospect.audit_engine.log_event"):
        _client().post("/a/ada", data=form, follow_redirects=False)
    assert create.call_args.kwargs["invitation_id"] is None
    responded.assert_not_called()


# ============================================================
# Pricing: the unit is the invitation
# ============================================================

def test_pricing_labels_speak_of_invitations():
    first = pricing_engine.prospect_quote(False)
    assert first["total_cents"] == 50000 and first["letters"] == 25
    assert "invitations" in first["label"]
    repeat = pricing_engine.prospect_quote(True, 40)
    assert repeat["total_cents"] == 80000 and "Invitations" in repeat["label"]
