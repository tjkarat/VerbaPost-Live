# Prospect Acquisition Path (advisor-branded free letter)

Runs alongside the CFP-buys-letter (heirloom) flow. Nothing in the heirloom
flow changed; this path adds routes, tables and an admin queue kind.

## The flow

1. Advisor sets up a page in the portal (`/advisor`, "Prospect Campaign" card):
   page address (`/a/{slug}`), name, firm, photo, return address, optional
   headline / intro / interview question / compliance footer.
2. Advisor buys letters. First campaign is a flat **$500 for 25 letters**;
   every later purchase is **$20 per letter**. Server-side quote
   (`pricing_engine.prospect_quote`) reads the ledger, so the button cannot
   choose its own price. Admin can also grant letters (`/admin`, "Prospect
   Campaigns") for deals invoiced by hand; a grant does not count as the
   first purchase.
3. Prospect opens `/a/{slug}`, enters name, phone, recipient name + address,
   ticks the express-written-consent box, submits.
4. Server: honeypot, per-IP rate limit, validation, capacity check
   (balance minus open reservations), 90-day per-phone dedupe, **consent
   record written**, **DNC scrub**, then the Twilio call.
5. Prospect answers, hears the recording disclosure and the question,
   speaks for up to 10 minutes.
6. Twilio posts to `/webhooks/twilio/recording` (unchanged endpoint). If the
   SID is not a heirloom draft it is matched to `prospect_letters`;
   Whisper transcribes, `refine_text` polishes, **one letter credit is
   consumed**, status becomes `Approved`, admin and advisor are emailed.
7. Admin print queue shows the letter (kind `prospect`) with letter PDF
   ("With the compliments of: Advisor, Firm", "For: Recipient", QR to
   `/play/p{id}`) and an envelope whose return address is the advisor.
   Mark Sent stamps `sent_at`.
8. Recipient scans the QR: `/play/p{id}` streams the audio. There is no
   advisor release gate on this path; hearing the voice is the gift.

## Tables (auto-created by `Base.metadata.create_all`; SQL in `infra/staging_schema.sql`)

| table | purpose |
|---|---|
| `advisor_pages` | one landing page per advisor |
| `prospect_letters` | **the send log** — one row per intake, never deleted |
| `prospect_credit_ledger` | letter balance = SUM(delta); `purchase` rows flip pricing to repeat |
| `dnc_suppressions` | internal do-not-call list (opt-outs, complaints) |

## Send log / CSV export

`/advisor/campaign/export.csv` (advisor's own rows) and
`/admin/prospect/export.csv` (everyone). Every column a records reviewer
could ask for: consent version, full consent text, timestamp, IP, user agent,
DNC status/provider/time, call SID and attempts, audio URL, letter version,
the letter text itself, queued/sent timestamps.

## Consent and DNC

* Consent text lives in `dnc_engine.CONSENT_TEXT`; bump `CONSENT_VERSION`
  when the wording changes. The form posts the version and the server
  rejects a stale one, so a cached page can never record consent to text the
  prospect did not see.
* `dnc_engine.scrub()` checks the internal list, then an optional external
  provider configured entirely by env vars:

  ```
  DNC_PROVIDER_NAME=vendor            label in the send log
  DNC_PROVIDER_URL=https://.../{phone} GET with {phone} substituted, else POST {"phone": ...}
  DNC_PROVIDER_KEY=...                 Authorization: Bearer
  DNC_PROVIDER_RESULT_KEY=on_dnc       JSON key; truthy = listed
  DNC_FAIL_CLOSED=1                    provider error blocks the dial (default)
  ```
  Without a provider the log records `internal_only`. That is the honest
  label: the number was checked against our list, not the national registry.
* Prospect can revoke from the confirmation page; the number goes on the
  internal list and no further dial happens.

## Not verified here

* No external DNC vendor was wired or tested against a live API; the hook is
  generic and covered by mocked tests only.
* Twilio, Whisper, Stripe and Resend are mocked in tests. The full path was
  exercised end-to-end against SQLite with only those four mocked.
* Whether TCPA prior-express-written-consent language, the recording
  disclosure, and FINRA 2210 record retention are sufficient for a given
  broker-dealer is a compliance question, not a code question. The advisor's
  compliance footer field exists for that reason.
