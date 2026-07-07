# Staging End-to-End Test Plan

**Environment:** https://staging.verbapost.com
**Time needed:** ~45–60 minutes (includes one real phone call)
**You need:** Stripe test card `4242 4242 4242 4242` (any future expiry/CVC/ZIP), a second email address for the heir — use the Gmail plus-trick: `tjkarat+heir@gmail.com` is a distinct account to Supabase but delivers to your normal inbox. **Never reuse the advisor's email as the heir** (one email = one account, and the advisor role wins). Run heir scenes in an incognito window so the two sessions don't collide, your cell phone, the staging Supabase dashboard open in another tab (Table Editor), and a terminal for the log command:

```
gcloud run services logs read verbapost-web-staging --region us-central1 --limit=50
```

**Rule:** work the scenes in order — later scenes consume what earlier scenes create. Note anything odd, even "felt slow." Screenshot every failure.

---

## Scene 0 — Pre-flight (one-time setup)

- [ ] Latest code deployed: GitHub Actions shows green on the newest `staging` commit
- [ ] RLS enabled: run the `ALTER TABLE ... ENABLE ROW LEVEL SECURITY;` block (7 tables) in staging Supabase SQL Editor
- [ ] Server key swapped: `SUPABASE_KEY` in `~/staging-env.yaml` = the **service_role** key; re-applied via `--env-vars-file`; then https://staging.verbapost.com/health returns ok
- [ ] `GA_ID: ""` in the env file (keeps test traffic out of prod analytics)

## Scene 1 — Public pages (5 min)

- [ ] Splash loads fast, orange STAGING banner, **no emoji anywhere**
- [ ] `/legal` renders (30-day window, NOT A LEGAL DOCUMENT)
- [ ] `/blog` lists 3 posts; open one; readable, styled
- [ ] Legacy redirects: `/?nav=login` → login page; `/?play=demo` → demo player plays audio
- [ ] Logged out, `/advisor` and `/heirloom` both bounce to `/login`

## Scene 2 — Auth (10 min)

- [ ] Sign up with a FRESH email → "check your email" notice
- [ ] Confirmation email arrives; link lands back on **staging** (not localhost)
- [ ] Log in → lands on `/heirloom` showing "Account Verification Pending" (guest mode — correct for a non-sponsored user)
- [ ] Log out → `/login` reachable again
- [ ] Wrong password → error message + the box **shakes**
- [ ] (Optional) Forgot password → reset code email → `/reset` works
- [ ] (Skip unless configured) Google OAuth round-trip

## Scene 3 — Advisor: money in (10 min)

Use your advisor account (role='advisor' in user_profiles).

- [ ] `/advisor` renders: firm name, credit count, roster, media locker
- [ ] Note current credit count: ____
- [ ] **Purchase Credit ($99)** → Stripe test checkout → pay with 4242 card
- [ ] Returned to **/advisor** with "payment received" banner (NOT the splash page)
- [ ] Within ~60s credits show +1 (refresh) — this is the webhook, not your browser
- [ ] Supabase check: `payment_fulfillments` has a new `cs_test_...` row
- [ ] Edit firm name → save → persists after refresh

## Scene 4 — Activation & the $40 add-on (10 min)

- [ ] Activate a client: heir name + your second email → success notice; advisor credits −1
- [ ] Welcome email arrives at heir address: formal design, addressed **by name**, firm name in subject and footer, button links to **staging**
- [ ] Roster shows the heir (name + email)
- [ ] Supabase check: heir's row in `user_profiles` has **credits = 1** (the included story)
- [ ] **Add Story ($40)** next to the heir → Stripe shows $40.00 → pay with 4242
- [ ] Supabase check: heir's credits now **2**; a second `payment_fulfillments` row exists
- [ ] Advisor's own credits UNCHANGED by the $40 purchase

## Scene 5 — The family: record a story (15 min, the big one)

Log out; log in as the heir (sign up with the second email first if you haven't — same address the advisor activated).

- [ ] `/heirloom` shows the real dashboard (NOT guest mode), "Sponsored by {firm}", story credits visible
- [ ] Enter your cell as storyteller phone; customize the question; **Start Interview Call**
- [ ] Phone rings; biographer speaks the firm name and YOUR question; record a couple of sentences; press `#`
- [ ] **Do nothing.** Within ~2 minutes, refresh: the story appears with your words transcribed (this is the webhook — no "Check for New Stories")
- [ ] Audio plays in the browser; download link works
- [ ] Edit the transcript → Save → persists. **AI Polish** → text gets cleaner
- [ ] Enter shipping address → saves, shows "Mailing to: …"
- [ ] **Mail Letter (1 credit)** → confirm → "Added to the print queue" notice; story credits −1
- [ ] YOUR inbox (admin): print-ready alert email with the content
- [ ] Supabase check: project status = "Approved"; `audit_events` has "Manual Print Queued"

## Scene 6 — The vault gate (5 min)

Get the story's project ID (Supabase `projects` table, or the audit log).

- [ ] Open `/play/{id}` logged OUT (incognito): **"THIS RECORDING IS SECURED"** — no audio player
- [ ] Try `/play/{id}/audio.mp3` directly: browser shows an error (403) — no side door
- [ ] Log in as advisor → Media Locker shows the story **Locked** → click **Release Audio**
- [ ] Incognito again: `/play/{id}` now plays the recording
- [ ] `/archive/{id}` shows the branded vault page ("Preserved by {firm}")
- [ ] (Optional) Lock it again → confirm `/play/{id}` re-locks

## Scene 7 — Wreckage sweep (5 min)

Try to break it:

- [ ] Double-click Mail Letter fast — only one credit consumed?
- [ ] Browser Back button after Stripe payment — no double credit?
- [ ] Garbage phone number in interview form → clean error, no call
- [ ] `/play/999999` → friendly not-found page, not a crash
- [ ] Phone browser: splash, login, and heirloom dashboard usable on mobile?

## Scene 8 — Evidence review (5 min)

- [ ] Cloud Run logs (command above): no tracebacks/ERROR lines from your session (email ✅ lines, webhook ok=True lines expected)
- [ ] Stripe (sandbox) → webhook destination → Event deliveries: all 200s
- [ ] Resend → Emails: all sends Delivered
- [ ] Supabase `audit_events`: a coherent story of everything you just did

---

## Verdict

**All scenes green** → staging is functionally cutover-ready; remaining work is Phase 4 (admin console) + final sweep + revision swap.
**Any scene red** → screenshot + the log command output → send to Claude; fixes have been landing same-day.

| Scene | Result | Notes |
|---|---|---|
| 0 Pre-flight | | |
| 1 Public | | |
| 2 Auth | | |
| 3 Advisor money | | |
| 4 Activation/$40 | | |
| 5 Family story | | |
| 6 Vault gate | | |
| 7 Wreckage | | |
| 8 Evidence | | |
