# VerbaPost — Security Review

_Manual code review of the full repository (Streamlit legacy app + FastAPI migration in `app/`), engines, data layer, payments, and config. Date: 2026-07-13._

Overall the codebase shows real security awareness — Stripe and Twilio webhooks verify signatures, SQL uses bound parameters, ownership checks exist on drafts/recipients, and secrets are kept out of git. The issues below are the exceptions worth fixing, ordered by severity.

---

## CRITICAL

### C1. Hardcoded fallback `SESSION_SECRET` allows session-cookie forgery → full admin takeover
**File:** `app/main.py:37-42`
```python
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET", "dev-only-secret-not-for-production"),
    ...
)
```
If `SESSION_SECRET` is not set in the environment, the app silently signs session cookies with a **known string that is published in the source code**. Auth in the FastAPI stack is entirely session-cookie based (`request.session["role"] = "admin"`). Anyone who knows the default secret can forge a cookie granting themselves `{"email": "<you>", "role": "admin"}` and take over the admin console, mark orders sent, grant unlimited credits, and read every family's queue.

This is only safe if the env var is _always_ set in production — a single missed env var = full compromise, with no visible symptom.

**Fix:** Fail fast instead of falling back. e.g.
```python
SECRET = os.environ.get("SESSION_SECRET")
if not SECRET:
    if ENV == "production":
        raise RuntimeError("SESSION_SECRET must be set in production")
    SECRET = "dev-only-secret-not-for-production"
```
Rotate the secret if the app has ever run in prod without it set (invalidates existing sessions — acceptable).

---

## HIGH

### H1. TwiML/XML injection via interview question → Twilio toll fraud
**File:** `ai_engine.py:57-79` (`trigger_outbound_call`)
The interview `question_text` (and `advisor_name`) are interpolated **unescaped** into a TwiML document:
```python
twiml = f"""
    <Response>
        ...
        <Say voice="Polly.Joanna-Neural">
            {question_text}
        </Say>
        ...
        <Record ... recordingStatusCallback="{recording_callback}" ... />
```
`question_text` originates from heir-supplied form input (`/heirloom/call`, `/heirloom/interview/save`) and is only `.strip()`ed. A user can submit a question like:
```
</Say><Dial><Number>+1900...</Number></Dial><Say>
```
Twilio will execute the injected verbs. `<Dial>` to premium-rate/international numbers is billed to **your** Twilio account → toll fraud, plus call redirection / social-engineering of the callee.

**Fix:** XML-escape all interpolated values (`xml.sax.saxutils.escape`) or, better, build TwiML with the official `twilio.twiml.VoiceResponse` builder which escapes for you.

### H2. HTML injection into outbound emails via unescaped merge fields
**File:** `email_engine.py` (multiple: `send_interview_prep_email`, `send_heir_welcome_email`, `send_admin_print_ready_alert`, etc.)
User/advisor-controlled values — `advisor_firm`, `advisor_name`, `question_text`, `heir_name`, `client_name`, `content_preview`, `user_email` — are interpolated directly into HTML email bodies via f-strings. An advisor (or anyone who can set a firm name / question) can inject arbitrary markup and links:
```python
html_content = f"""... <strong>{advisor_firm}</strong> ..."""
```
Because these emails are sent **from VerbaPost's trusted domain** to heirs/clients, this is an effective phishing vector (inject a malicious "Enter the Archive" link) and can break rendering.

**Fix:** HTML-escape every merge field (`markupsafe.escape` / `html.escape`) before interpolation, or render via a Jinja2 template with autoescaping (you already use Jinja2 for the web pages).

---

## MEDIUM

### M1. Hardcoded admin emails, including a typosquat address
**File:** `main.py:106-114` (root Streamlit app)
```python
is_admin = (
    (st.session_state.user_role == "admin") or
    (user_email == "tjkarat@gmail.com") or
    (user_email == "tjkarat@gmai.com") or   # <-- typo domain "gmai.com"
    (user_email == "pat@gmail.com")
)
```
`gmai.com` is a real, known typosquatting domain — if it has a catch-all, someone could register `tjkarat@gmai.com`, authenticate, and receive admin. `pat@gmail.com` is a generic address that is not yours. Grants of admin should not depend on string-matching arbitrary emails.

**Fix:** Remove all hardcoded emails; drive admin purely from a DB `role` / single `ADMIN_EMAIL` env var (as the FastAPI app already does). Delete the typo and `pat@gmail.com` entries immediately.

### M2. Credit balances updated with non-atomic read-modify-write (double-spend)
**Files:** `database.py` (`add_advisor_credit`, `update_user_credits`), `app/heirloom.py:293-320` (`queue_letter`), `app/advisor.py:100-111`
Credits are read into Python, decremented, then written back (`database.update_user_credits(email, credits - CREDIT_COST)`). Two concurrent requests can both read the same balance and each spend it → a user mails multiple letters (or activates multiple clients) on a single credit. Same TOCTOU pattern in `add_advisor_credit` (select-then-update).

**Fix:** Use an atomic DB update (`UPDATE ... SET credits = credits - 1 WHERE email = :e AND credits >= 1` and check rowcount), or a Postgres RPC / row lock. Never compute the new balance in application code.

### M3. PII enumeration via sequential IDs on public endpoints
**Files:** `app/player.py` (`/play/{id}`), `app/heirloom.py:330` (`/archive/{pid}`), `database.py:615` (`get_public_draft`), `get_project_by_id`
The QR/archive pages take an integer project ID and return `heir_name`, `parent_name`, and `firm_name` for that project **with no authentication**. Audio playback is correctly gated behind the `audio_released` flag, but the names are not — an attacker can walk IDs (1, 2, 3, …) and harvest family/heir/advisor-firm relationships (client-list PII for a wealth-management product).

**Fix:** Use unguessable IDs for public links (UUID or a signed token) instead of sequential integers, and/or return minimal data until the viewer proves they hold the QR token.

### M4. Admin audio proxy forwards attacker-influenced path with Twilio credentials
**File:** `app/admin.py:275-284` (`/admin/orphan-audio?uri=`)
```python
if not uri.startswith("/"):
    return Response(status_code=400)
audio = ai_engine.fetch_recording_audio(uri)   # -> GET https://api.twilio.com{uri} with account creds
```
The `uri` query param is attacker-controlled (admin-only) and is appended to `https://api.twilio.com` and requested with your Twilio **basic-auth credentials**. The host is effectively locked to `api.twilio.com` and this is behind the admin gate, so impact is limited, but it lets a request carry account creds to an arbitrary Twilio path and follows redirects by default.

**Fix:** Validate `uri` against the expected recording path shape (`/2010-04-01/Accounts/AC.../Recordings/RE....mp3`), and pass `allow_redirects=False` on the `requests.get`.

---

## LOW / Hygiene

- **L1. `local_audit.db` was committed to git history** (commits `4b9dea1`, then removed in `a270f94`). The blob in history contains only a `validation_test@verbapost.com` test row — no real PII or secrets — so impact is low, but SQLite DBs should never enter history. It's now correctly gitignored. Consider a history purge only if a real DB was ever committed on another branch.
- **L2. Streamlit `enableCORS = false`** (`.streamlit/config.toml`) also disables Streamlit's XSRF protection. Low impact given the migration to FastAPI, but avoid on the live Streamlit app.
- **L3. No CSRF tokens** on FastAPI state-changing POSTs. Partially mitigated by `same_site="lax"` session cookies. Add per-form CSRF tokens before relying on this app for higher-value actions. Also note `/advisor/checkout` and `/advisor/story/checkout` are GETs that create Stripe sessions — prefer POST for side-effecting routes.
- **L4. `requests.get` without timeout** in `ai_engine.fetch_recording_audio` and `find_and_transcribe_recording` — a hung Twilio response can pin a worker. The webhook path already sets `timeout=60`; do the same everywhere.
- **L5. Verbose error disclosure** — several handlers surface raw exceptions to users (e.g. `payment_engine.py:198` `st.error(f"Payment Error: {e}")`). Log the detail server-side; show a generic message to users.
- **L6. Broad `except: pass` / `except Exception: return {}`** throughout `database.py` and engines silently swallows failures, including security-relevant ones (e.g. ownership/DB errors returning empty), which hampers monitoring and can mask attacks. Log before swallowing.

---

## What's already done well
- Stripe webhook verifies `construct_event` signatures; Twilio webhook validates `X-Twilio-Signature` (with correct proto reconstruction behind Cloud Run). (`app/webhooks.py`)
- Payment fulfillment is idempotent via the `payment_fulfillments` table.
- SQL uses SQLAlchemy bound parameters everywhere; the only f-string SQL uses table names from fixed internal maps, not user input.
- Draft/recipient/release actions enforce server-side ownership checks (`_owns_draft`, `delete_recipient`, `toggle_release`).
- `get_public_draft` casts the ID to `int` to defuse injection, and the audio proxy keeps Twilio creds server-side.
- Secrets are gitignored (`.streamlit/secrets.toml`, `.env`) and were never committed; the `sk_live_...` strings in `AI_RULES.md`/tests are placeholders.
- FastAPI admin gating reads `role == "admin"` from the signed session, set only when `email == ADMIN_EMAIL` (no hardcoded list) — the pattern the legacy app should adopt (see M1).

---

## Suggested fix order
1. **C1** — set/guard `SESSION_SECRET` (fastest, highest impact).
2. **H1** — escape TwiML (direct financial exposure via toll fraud).
3. **H2** — escape email merge fields.
4. **M1** — remove hardcoded/typo admin emails.
5. **M2** — atomic credit updates.
6. **M3/M4** and the Low items as hardening.
