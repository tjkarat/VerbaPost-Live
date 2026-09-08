# Prospect Acquisition Path (advisor-branded free letter)

Runs alongside the CFP-buys-letter (heirloom) flow. Nothing in the heirloom
flow changed; this path adds routes, tables and an admin queue kind.

## The billable unit

The **invitation mailed** is what costs money: $20 each, first campaign a flat
$500 for 25. The story letter a responder earns — call, transcription, linen
letter, QR, postage — is **included**, and consumes no credit. That keeps the
pitch in language an advisor already prices seminars in: cost per name mailed.

The landing page is still gated, by `database.prospect_story_allowance()`
(everything bought, minus stories already produced, minus intakes in flight),
so a personal link forwarded around can't run up unlimited Twilio and print
costs on one campaign.

## The flow

1. Advisor sets up a page in the portal (`/advisor`, "Prospect Campaign" card):
   page address (`/a/{slug}`), name, firm, photo, return address, optional
   headline / intro / interview question / invitation body / compliance footer.
2. Advisor buys invitations. First campaign is a flat **$500 for 25**; every
   later purchase is **$20 each**. Server-side quote
   (`pricing_engine.prospect_quote`) reads the ledger, so the button cannot
   choose its own price. Admin can also grant invitations (`/admin`, "Prospect
   Campaigns") for deals invoiced by hand; a grant does not count as the
   first purchase.
3. **Advisor uploads a mailing list** (CSV: Name or First/Last, Address, City,
   State, ZIP). `campaign_engine.parse_mailing_list` normalizes states and
   ZIPs (including Excel-stripped leading zeros), reports unusable rows, drops
   in-file duplicates, and the upload route drops households this advisor has
   already mailed. Nothing is mailed and nothing is billed at this point: the
   advisor sees a review screen, can open a proof of the exact letter, and
   only then clicks Send.
4. **Each invitation is mailed via PostGrid** with the advisor's return
   address and that person's own link and QR (`/a/{slug}/i/{token}`). One
   ledger credit is consumed per letter PostGrid accepts — never before. A
   failed row costs nothing and can be retried; PostGrid's `Idempotency-Key`
   (`invite:{id}`) makes a retry incapable of printing twice.
5. Prospect follows their personal link. The page greets them by name and
   pre-fills it; they enter phone, recipient name + address, tick the
   express-written-consent box, submit. The response is tied back to the
   invitation (`prospect_letters.invitation_id`), which is how response rate
   is provable to the advisor.
6. Server: honeypot, per-IP rate limit, validation, story-allowance check,
   90-day per-phone dedupe, **consent record written**, **DNC scrub**, then
   the Twilio call.
7. Prospect answers, hears the recording disclosure and the question,
   speaks for up to 10 minutes.
8. Twilio posts to `/webhooks/twilio/recording` (unchanged endpoint). If the
   SID is not a heirloom draft it is matched to `prospect_letters`;
   Whisper transcribes, `refine_text` polishes, status becomes `Approved`,
   admin and advisor are emailed. No credit is consumed here.
9. Admin print queue shows the letter (kind `prospect`) with letter PDF
   ("With the compliments of: Advisor, Firm", "For: Recipient", QR to
   `/play/p{id}`) and an envelope whose return address is the advisor.
   Mark Sent stamps `sent_at`.
10. Recipient scans the QR: `/play/p{id}` streams the audio. There is no
    advisor release gate on this path; hearing the voice is the gift.

## Tables (auto-created by `Base.metadata.create_all`; SQL in `infra/staging_schema.sql`)

| table | purpose |
|---|---|
| `advisor_pages` | one landing page per advisor (plus the invitation body) |
| `prospect_campaigns` | one uploaded mailing list |
| `campaign_invitations` | one row per name mailed: token, address, PostGrid id, status, who responded |
| `prospect_letters` | **the send log** — one row per intake, never deleted |
| `prospect_credit_ledger` | invitation balance = SUM(delta); `purchase` rows flip pricing to repeat |
| `dnc_suppressions` | internal do-not-call list (opt-outs, complaints) |

## Send log / CSV export

`/advisor/campaign/export.csv` (advisor's own rows) and
`/admin/prospect/export.csv` (everyone). Every column a records reviewer
could ask for: consent version, full consent text, timestamp, IP, user agent,
DNC status/provider/time, call SID and attempts, audio URL, letter version,
the letter text itself, queued/sent timestamps, and the invitation the
response came from.

`/advisor/campaign/{id}/rows.csv` is the per-mailing view: every name, its
PostGrid id or failure reason, and the story letter it produced.

## Mailing mechanics

Two providers behind one function. `MAIL_PROVIDER` picks (`pcm` | `postgrid`);
with no explicit value it is PCM whenever `PCM_API_KEY` exists.

* **PCM (PostcardMania)** — confirmed against PCM's own OpenAPI 3.0 spec
  (DirectMail API v3), not inference:
  1. `POST {PCM_BASE_URL}/auth/login` with `{apiKey, apiSecret}` returns a
     short-lived JWT (`{token, expires}`). Every other PCM call authenticates
     with that JWT as `Authorization: Bearer`, not with the API key/secret
     directly. `mailer.py` caches the token and re-logs-in ~60s before it
     expires.
  2. `POST {PCM_BASE_URL}/order/letter`, `Authorization: Bearer <token>`,
     JSON body -> `201 {batchID, orderID, extRefNbr}`. We store `orderID` and
     pass `invite:{id}` as `extRefNbr` (both on the order and on the one
     recipient in it), which comes back on every PCM webhook about that
     piece, so mail-tracking events can be joined to the invitation.
  3. PCM's `letter` field — the artwork — takes **raw HTML or a URL it
     fetches**, never a binary/base64 upload, and it is one value for the
     whole order, not per recipient. Since every prospect's invitation is
     personalized (their own QR + link), each PCM order carries exactly one
     recipient, and `letter` points at
     `{BASE_URL}/a/{slug}/i/{token}/pdf` — a new, unauthenticated route that
     regenerates that one person's exact PDF on request. Unauthenticated is
     deliberate: PCM's servers fetch it, not a logged-in advisor, and the
     token is already the entire security model of the personal link itself.
  4. `insertAddressingPage: true` + `envelope.type: "fullWindow"` tells PCM
     to generate its own address page rather than requiring us to pre-print
     the address into the artwork, so `invitation_format.py`'s blank top
     zone (built for PostGrid's overlay convention) is simply unused space
     on a PCM send — harmless, not wrong.
  5. Sandbox vs Production is **which `apiKey`/`apiSecret` pair you used**,
     not a different host — PCM's spec lists exactly one server. There is no
     API-visible way to ask which environment a key belongs to, so
     `PCM_ENVIRONMENT=sandbox|production` is set by hand to match whichever
     pair is in `PCM_API_KEY`/`PCM_API_SECRET`, purely so the portal can
     label a run "test mode" truthfully.
* **PostGrid** — the previous path, kept as fallback:
  `addressPlacement=top_first_page` plus an `Idempotency-Key` header.
* `mailer.is_test_mode()` follows `PCM_ENVIRONMENT` for PCM, or a `test_`
  PostGrid key. The portal says so in plain words before and after a send, so
  a staging run is never mistaken for real mail.
* Sends run as a FastAPI background task, so a 200-name list does not hold the
  request open. The portal's mailing table shows progress on refresh.

### Before mailing a real advisor list

`GET /admin/pcm/probe` (admin only) places one real letter order addressed to
VerbaPost itself and returns PCM's raw status and body — a live smoke test
of credentials, login, and the order call together, now that the schema
itself is confirmed rather than guessed. Point `PCM_API_KEY`/`PCM_API_SECRET`
at a **Sandbox** key pair the first time you run it; only re-run it against
Production once you're ready for a real, billed test letter.

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
* Neither mail provider has been called for real yet. The PCM request/response
  shapes above are confirmed from PCM's own OpenAPI spec, not inference, but
  that is not the same as a live order having actually succeeded. Sequence
  for going live: `/admin/pcm/probe` against a Sandbox `apiKey`/`apiSecret`
  pair until it returns `ok`, then one row addressed to yourself with a
  Production pair, then an advisor's list.
* Twilio, Whisper, Stripe, PCM, PostGrid and Resend are mocked in tests. The
  full path was exercised end-to-end against SQLite with only those mocked.
* Nothing verifies that an uploaded list was lawfully sourced, or suppresses
  against a mail preference service. That is the advisor's representation to
  make; consider putting it in your advisor agreement.
* Whether TCPA prior-express-written-consent language, the recording
  disclosure, and FINRA 2210 record retention are sufficient for a given
  broker-dealer is a compliance question, not a code question. The advisor's
  compliance footer field exists for that reason.
