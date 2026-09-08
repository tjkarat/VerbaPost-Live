"""
Invitation campaigns — the mass-mail side of the prospect acquisition path.

    advisor uploads CSV  ->  parse_mailing_list()  ->  draft campaign
    advisor clicks Send  ->  send_campaign()       ->  one PostGrid letter per row

Billing rule (financial atomicity, per AI_RULES.md): a ledger credit is
consumed ONLY after PostGrid accepts the letter. Rows that fail stay
'failed' and cost nothing; rows that can't be sent because the balance ran
out are 'skipped' so the advisor can top up and re-send.
"""

import csv
import io
import logging
import re
from datetime import datetime

import database
import invitation_format
import mailer

logger = logging.getLogger(__name__)

MAX_ROWS_PER_UPLOAD = 500

# Header aliases -> canonical field. Lower-cased, non-alphanumerics stripped.
_HEADER_MAP = {
    "fullname": "full_name", "name": "full_name", "recipient": "full_name", "prospect": "full_name",
    "firstname": "first_name", "first": "first_name", "givenname": "first_name",
    "lastname": "last_name", "last": "last_name", "surname": "last_name", "familyname": "last_name",
    "address": "line1", "address1": "line1", "addressline1": "line1", "street": "line1",
    "streetaddress": "line1", "line1": "line1", "mailingaddress": "line1",
    "address2": "line2", "addressline2": "line2", "line2": "line2", "apt": "line2", "unit": "line2", "suite": "line2",
    "city": "city", "town": "city",
    "state": "state", "st": "state", "province": "state", "region": "state",
    "zip": "zip_code", "zipcode": "zip_code", "postal": "zip_code", "postalcode": "zip_code", "zip5": "zip_code",
}

_US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI", "ID", "IL", "IN", "IA",
    "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM",
    "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA",
    "WV", "WI", "WY", "PR", "VI", "GU", "AS", "MP", "AA", "AE", "AP",
}
_STATE_BY_NAME = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA", "colorado": "CO",
    "connecticut": "CT", "delaware": "DE", "district of columbia": "DC", "florida": "FL", "georgia": "GA",
    "hawaii": "HI", "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD", "massachusetts": "MA",
    "michigan": "MI", "minnesota": "MN", "mississippi": "MS", "missouri": "MO", "montana": "MT",
    "nebraska": "NE", "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM",
    "new york": "NY", "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC", "south dakota": "SD",
    "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY", "puerto rico": "PR",
}


def _norm_header(h):
    return re.sub(r"[^a-z0-9]", "", (h or "").lower())


def _norm_state(raw):
    s = (raw or "").strip()
    if len(s) == 2 and s.upper() in _US_STATES:
        return s.upper()
    return _STATE_BY_NAME.get(s.lower(), "")


def _norm_zip(raw):
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 9:
        return f"{digits[:5]}-{digits[5:]}"
    if len(digits) == 5:
        return digits
    # Excel strips leading zeros from New England ZIPs: 2134 -> 02134
    if len(digits) == 4:
        return "0" + digits
    return ""


def parse_mailing_list(data: bytes):
    """
    CSV bytes -> (rows, problems, mapping)
      rows:     [{full_name, first_name, line1, line2, city, state, zip_code}]
      problems: [(line_no, reason)] for rows we could not use
      mapping:  {canonical_field: original_header} for the review screen
    """
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("latin-1")
    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
    except StopIteration:
        return [], [(0, "The file is empty.")], {}

    mapping = {}
    idx = {}
    for i, h in enumerate(header):
        field = _HEADER_MAP.get(_norm_header(h))
        if field and field not in idx:
            idx[field] = i
            mapping[field] = h

    have_name = "full_name" in idx or "first_name" in idx
    missing = [f for f in ("line1", "city", "state", "zip_code") if f not in idx]
    if not have_name or missing:
        need = (["a name column"] if not have_name else []) + missing
        return [], [(0, "Couldn't find " + ", ".join(need) + " in the header row. "
                        "Expected columns like: Name (or First, Last), Address, City, State, ZIP.")], mapping

    rows, problems = [], []
    seen = set()
    for n, raw in enumerate(reader, start=2):
        if not any((c or "").strip() for c in raw):
            continue
        if len(rows) >= MAX_ROWS_PER_UPLOAD:
            problems.append((n, f"Stopped at {MAX_ROWS_PER_UPLOAD} rows; split the file."))
            break

        def col(f):
            i = idx.get(f)
            return (raw[i].strip() if i is not None and i < len(raw) else "")

        first, last = col("first_name"), col("last_name")
        full = col("full_name") or (first + " " + last).strip()
        if not first and full:
            first = full.split(" ")[0]
        line1, line2, city = col("line1"), col("line2"), col("city")
        state, zip_code = _norm_state(col("state")), _norm_zip(col("zip_code"))

        if len(full) < 2:
            problems.append((n, "missing name")); continue
        if len(line1) < 3:
            problems.append((n, "missing street address")); continue
        if len(city) < 2:
            problems.append((n, "missing city")); continue
        if not state:
            problems.append((n, f"unrecognized state '{col('state')}'")); continue
        if not zip_code:
            problems.append((n, f"bad ZIP '{col('zip_code')}'")); continue

        key = (line1.lower(), zip_code[:5], full.lower())
        if key in seen:
            problems.append((n, "duplicate of an earlier row")); continue
        seen.add(key)
        rows.append({"full_name": full[:120], "first_name": (first or full.split(" ")[0])[:60],
                     "line1": line1[:120], "line2": line2[:60] or None, "city": city[:80],
                     "state": state, "zip_code": zip_code})
    return rows, problems, mapping


def personal_url(base_url, slug, token):
    return f"{base_url.rstrip('/')}/a/{slug}/i/{token}"


def build_invitation_pdf(page, invitation, base_url):
    return invitation_format.create_invitation_pdf(
        first_name=invitation.get("first_name") or invitation.get("full_name"),
        personal_url=personal_url(base_url, page["slug"], invitation["token"]),
        advisor_name=page.get("display_name"), firm_name=page.get("firm_name"),
        body=page.get("invite_body"), disclosure=page.get("disclosure"))


def send_campaign(campaign_id, base_url):
    """
    Mail every pending invitation in the campaign. Safe to call again after
    a partial run: sent rows are skipped, and PostGrid's idempotency key
    (invite:{id}) means a retried row can never print twice.
    Returns (sent, failed, skipped).
    """
    camp = database.get_campaign(campaign_id)
    if not camp:
        return 0, 0, 0
    advisor_email = camp["advisor_email"]
    page = database.get_advisor_page_by_email(advisor_email) or {}
    if not page.get("slug"):
        database.update_campaign(campaign_id, status="failed")
        return 0, 0, 0
    database.update_campaign(campaign_id, status="sending")

    from_addr = {"name": page.get("display_name") or "", "company": page.get("firm_name") or "",
                 "line1": page.get("return_line1") or "", "city": page.get("return_city") or "",
                 "state": page.get("return_state") or "", "zip": page.get("return_zip") or ""}

    sent = failed = skipped = 0
    for inv in database.list_invitations(campaign_id=campaign_id, statuses=["pending", "failed"]):
        # Balance check per row: invitations are the billable unit.
        if database.prospect_credit_balance(advisor_email) <= 0:
            database.update_invitation(inv["id"], status="skipped", skip_reason="no invitations remaining")
            skipped += 1
            continue
        pdf = build_invitation_pdf(page, inv, base_url)
        if not pdf:
            database.update_invitation(inv["id"], status="failed", error="PDF generation failed")
            failed += 1
            continue
        to_addr = {"name": inv["full_name"], "line1": inv["line1"], "line2": inv.get("line2"),
                   "city": inv["city"], "state": inv["state"], "zip": inv["zip_code"]}
        pg_id, err = mailer.send_invitation_letter(
            pdf, to_addr, from_addr,
            description=f"VerbaPost invitation {campaign_id}/{inv['id']} for {advisor_email}",
            idempotency_key=f"invite:{inv['id']}")
        if pg_id:
            # Artifact secured (PostGrid accepted) -> now, and only now, the ledger.
            database.update_invitation(inv["id"], status="sent", postgrid_id=pg_id,
                                       sent_at=datetime.utcnow(), error=None)
            database.add_prospect_credits(advisor_email, -1, "consume", f"invite:{inv['id']}")
            sent += 1
        else:
            database.update_invitation(inv["id"], status="failed", error=(err or "unknown")[:300])
            failed += 1

    all_rows = database.list_invitations(campaign_id=campaign_id)
    total_sent = sum(1 for r in all_rows if r["status"] == "sent")
    total_failed = sum(1 for r in all_rows if r["status"] == "failed")
    pending_left = sum(1 for r in all_rows if r["status"] in ("pending", "skipped"))
    status = "sent" if (total_failed == 0 and pending_left == 0) else "partial"
    database.update_campaign(campaign_id, status=status, sent_count=total_sent,
                             failed_count=total_failed, sent_at=datetime.utcnow())
    database.log_event(advisor_email, "Invitation Campaign Sent",
                       {"campaign_id": campaign_id, "sent": sent, "failed": failed, "skipped": skipped,
                        "test_mode": mailer.is_test_mode()})
    return sent, failed, skipped
