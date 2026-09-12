# Production End-to-End Test Plan

**Environment:** https://app.verbapost.com  (Cloud Run service `verbapost-app`, project `verbapost-prod`)
**Time needed:** ~60 minutes (includes one real phone call)
**Nature of this test:** This runs against **LIVE production** — real Stripe charges, real emails to real inboxes, a real phone call, and rows written to the **production** database.

> ⚠️ **READ FIRST — this test spends real money and writes real data.**
> - Stripe is in **live mode**: you will be charged **$99 + $40 = $139** on a real card. You refund both at the end (Scene 9).
> - Accounts, projects, and payment rows land in the **production** Supabase — plan to clean them up (Scene 9) or tag them clearly as test data.
> - Production has Google Analytics on, so this traffic hits your GA4. Acceptable for a one-off; note the timestamp so you can exclude it later if you care.
> - Do this during a quiet window; you're exercising the live checkout and telephony.

**You need:** a real credit card (yours), your cell phone, a second email for the heir via the Gmail plus-trick (`tjkarat+heir@gmail.com` — a distinct Supabase account that still lands in your inbox; **never reuse the advisor email as the heir**), an incognito window for heir/logged-out scenes, the **production** Supabase dashboard open (Table Editor), the Stripe **live** dashboard, the Resend dashboard, and a terminal for logs:

```
gcloud run services logs read verbapost-app --region us-central1 --project verbapost-prod --limit=50
```

**Rule:** work the scenes in order — later scenes consume what earlier scenes create. Screenshot every failure. Note anything odd, even "felt slow."

---

## Scene 0 — Pre-flight

- [ ] Latest deploy is green: `gh run list --workflow=deploy-prod.yml` shows the most recent run ✓, built from the intended `main` commit
- [ ] `https://app.verbapost.com/health` returns `{"status":"ok","env":"production"}`
- [ ] **No** orange STAGING banner anywhere on the site (that banner only shows when `ENV=staging`)
- [ ] Prod env vars set on `verbapost-app`: `SESSION_SECRET`, `ADMIN_EMAIL`, live `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET`, `TWILIO_ACCOUNT_SID` + `TWILIO_AUTH_TOKEN`, `OPENAI_API_KEY`, `RESEND_API_KEY` + `EMAIL_SENDER`, `SUPABASE_URL` + `SUPABASE_KEY` (service_role), `BASE_URL=https://app.verbapost.com`
- [ ] RLS enabled on the production Supabase tables (advisors, clients, projects, letter_drafts, user_profiles, recipients, audit_events)
- [ ] The Stripe **live** webhook endpoint points at `https://app.verbapost.com/webhooks/stripe` and is enabled for `checkout.session.completed`
- [ ] Twilio recording callback resolves to prod: `WEBHOOK_BASE_URL` (or `BASE_URL`) = `https://app.verbapost.com`

## Scene 1 — Public pages & recent UI changes (7 min)

- [ ] Splash loads fast; hero headline reads **"The Family Legacy Archive"** (no duplicate giant "VerbaPost"); **no emoji** anywhere
- [ ] Header wordmark "VerbaPost" is the **enlarged** size (1.85rem) — noticeably bigger than before
- [ ] `/login` heading reads **"Welcome"** (not "Welcome to VerbaPost"); tagline beneath it
- [ ] `/legal` renders (60-day window language; "NOT A LEGAL DOCUMENT")
- [ ] `/blog` lists posts; open one — readable, styled
- [ ] Legacy redirects: `/?nav=login` → `/login`; `/?play=demo` → demo player plays audio
- [ ] Logged out, `/advisor` and `/heirloom` both bounce to `/login`

## Scene 1b — Mobile layout (5 min, on your actual phone)

Open https://app.verbapost.com on your phone (or Chrome DevTools device mode at ~375px):

- [ ] Splash: header stacks/centers, nav links wrap and are tappable, hero + cards render single-column, buttons are full-width
- [ ] `/login`: form is comfortably usable; "Welcome" heading; inputs and buttons full-width, no horizontal scroll
- [ ] `/advisor` and `/heirloom` (after logging in later) are usable on the phone — revisit during Scene 3/5

## Scene 2 — Auth (10 min)

- [ ] Sign up with a FRESH email → "check your email" notice
- [ ] Confirmation email arrives; link lands back on **app.verbapost.com** (not localhost/staging)
- [ ] Log in → lands on `/heirloom` in guest/"verification pending" mode (correct for a non-sponsored user)
- [ ] Log out → `/login` reachable again
- [ ] Wrong password → error message + the box **shakes**
- [ ] Forgot password → reset code email → `/reset` accepts the code and sets a new password
- [ ] **Google OAuth round-trip:** "Continue with Google" → Google consent → back to `/heirloom` logged in.
      - Known/expected: the consent screen still shows the raw `…supabase.co` domain — that's the pending Custom-Domain item, not a bug. Just confirm the round-trip **works** and lands back on the app.

## Scene 3 — Advisor: money in (10 min) — REAL $99 CHARGE

Use your advisor account (role='advisor' in `user_profiles`).

- [ ] `/advisor` renders: firm name, credit count, roster, media locker
- [ ] Note current credit count: ______
- [ ] **Security check (email escaping / H2):** set the firm name to something with markup, e.g. `Test & <b>Co</b>`, and save. It should display as literal text, and the heir welcome email in Scene 4 must show it as text — **not** rendered bold / not an injected tag.
- [ ] **Purchase Credit ($99)** → Stripe **live** checkout → pay with your real card
- [ ] Returned to **/advisor** with "payment received" banner (NOT the splash page)
- [ ] Within ~60s credits show **+1** (refresh) — this is the webhook, not your browser
- [ ] Supabase check: `payment_fulfillments` has a new `cs_live_…` row
- [ ] Stripe live dashboard shows the $99 payment succeeded

## Scene 4 — Activation & the $40 add-on (10 min) — REAL $40 CHARGE

- [ ] Activate a client: heir name + your **second** email → success notice; advisor credits **−1**
- [ ] Welcome email arrives at the heir address: formal design, addressed **by name**, firm name in subject + footer, button links to **app.verbapost.com**
- [ ] Confirm the firm-name markup from Scene 3 renders as **plain text** in this email (email-escaping fix verified)
- [ ] Roster shows the heir (name + email)
- [ ] Supabase check: heir's `user_profiles` row has **credits = 1** (the included story)
- [ ] **Add Story ($40)** next to the heir → Stripe shows **$40.00** → pay with real card
- [ ] Supabase check: heir's credits now **2**; a second `payment_fulfillments` row exists
- [ ] Advisor's own credits UNCHANGED by the $40 purchase

## Scene 5 — The family: record a story (15 min, the big one) — REAL PHONE CALL

Log out; log in as the heir (sign up with the second email first if needed — same address the advisor activated).

- [ ] `/heirloom` shows the real dashboard (NOT guest mode), "Sponsored by {firm}", story credits visible
- [ ] **Security check (TwiML injection / H1):** in the interview **question** field, paste a payload such as
      `</Say><Dial><Number>+19005551234</Number></Dial><Say>hello`
      then start the call. **Expected:** the biographer either reads the text literally or it's inert — **no** call is dialed to that number, and the call proceeds normally. (If the call tried to dial out, stop and flag it — the escaping regressed.)
- [ ] Now run a clean call: enter your cell as storyteller phone; a normal question; **Start Interview Call**
- [ ] Phone rings; biographer speaks the firm name and YOUR question; record a couple of sentences; press `#`
- [ ] **Do nothing.** Within ~2 minutes, refresh: the story appears with your words transcribed (webhook push)
- [ ] Audio plays in the browser; download link works
- [ ] Edit the transcript → Save → persists. **AI Polish** → text gets cleaner
- [ ] Enter shipping address → saves, shows "Mailing to: …"
- [ ] **Mail Letter (1 credit)** → confirm → "Added to the print queue" notice; story credits **−1**
- [ ] YOUR inbox (admin `ADMIN_EMAIL`): print-ready alert email with the content + mailing list
- [ ] Supabase check: project status = "Approved"; `audit_events` has "Manual Print Queued"

## Scene 6 — The vault gate (5 min)

Get the story's project ID (Supabase `projects` table or the audit log).

- [ ] Open `/play/{id}` logged OUT (incognito): **locked** state ("secured" message) — no audio player
- [ ] Try `/play/{id}/audio.mp3` directly: **403**, no audio — no side door
- [ ] Log in as advisor → Media Locker shows the story **Locked** → click **Release Audio**
- [ ] Incognito again: `/play/{id}` now plays the recording
- [ ] `/archive/{id}` shows the branded vault page ("Preserved by {firm}")
- [ ] (Optional) Lock it again → confirm `/play/{id}` re-locks

## Scene 7 — Security & admin gate (5 min)

- [ ] **Admin gating (M1):** while logged in as the **heir** (non-admin), visit `/admin` → you are bounced to `/login` (or denied), NOT shown the console
- [ ] Log in as the admin (`ADMIN_EMAIL`) → `/admin` loads: health panel, print queue, credits, marketing
- [ ] In `/admin`, the print queue shows the Scene 5 story; "Mark Sent" closes it
- [ ] Health panel shows Stripe / Twilio / Resend / DB all green
- [ ] (Spot check) No hardcoded admin backdoor: a random logged-in non-admin cannot reach `/admin`

## Scene 8 — Wreckage sweep (5 min)

Try to break it:

- [ ] Double-click **Mail Letter** fast — only **one** credit consumed? (If two, flag the known credit-race item M2.)
- [ ] Browser **Back** after Stripe payment — no double credit? (`payment_fulfillments` idempotency should hold)
- [ ] Garbage phone number in the interview form → clean error, no call
- [ ] `/play/999999` → friendly not-found page, not a crash
- [ ] `/archive/999999` → friendly not-found, not a crash

## Scene 9 — Evidence, refunds & cleanup (8 min)

**Evidence:**
- [ ] Cloud Run logs (command at top): no tracebacks/ERROR lines from your session; expect email ✅ lines and webhook `ok=True` lines; **no secrets printed**
- [ ] Stripe (live) → your webhook endpoint → Event deliveries: all **200s**
- [ ] Resend → Emails: all sends **Delivered**
- [ ] Supabase `audit_events`: a coherent trail of everything you just did

**Refund the real charges:**
- [ ] Stripe live dashboard → refund the **$99** payment (full)
- [ ] Stripe live dashboard → refund the **$40** payment (full)

**Clean up test data (production DB):**
- [ ] Delete or clearly tag the test heir account (`user_profiles` + `clients` rows for `tjkarat+heir@…`)
- [ ] Delete the test `projects` / `letter_drafts` rows and the two `payment_fulfillments` rows (or leave, but note they exist)
- [ ] Reset your advisor `credits` back to its Scene 3 starting value if the test skewed it

---

## Verdict

**All scenes green** → production cutover verified end-to-end, including the recent UI and security changes.
**Any scene red** → screenshot + the log-command output → send it over.

| Scene | Result | Notes |
|---|---|---|
| 0 Pre-flight | | |
| 1 Public / UI | | |
| 1b Mobile | | |
| 2 Auth | | |
| 3 Advisor $99 | | |
| 4 Activation / $40 | | |
| 5 Family story + TwiML check | | |
| 6 Vault gate | | |
| 7 Security / admin gate | | |
| 8 Wreckage | | |
| 9 Evidence / refunds / cleanup | | |

---

### Optional: cheaper dry-run first
If you'd rather not spend real money to shake out obvious breakage, run Scenes 0–2, 6, 7, 8 (all free) on production first, and only do the paid Scenes 3–5 once those are green. The paid scenes are the only ones that touch live Stripe/telephony.
