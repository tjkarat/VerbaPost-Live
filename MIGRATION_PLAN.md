# VerbaPost Migration Plan: Streamlit → FastAPI + HTMX

**Approach:** Incremental (strangler pattern) — new service runs beside Streamlit; flows move one at a time.
**Date:** July 4, 2026

---

## 1. Current State (what I reviewed)

- **Repos:** `VerbaPost-Live` is production (~4,600 lines Python, 1,853 commits). `VerbaPost-App` appears to be the older B2C prototype — this plan targets `VerbaPost-Live`.
- **Frontend/backend:** Single Streamlit container (Python 3.9-slim + ffmpeg) on Cloud Run at `app.verbapost.com`. `verbapost.com` is a static marketing page (fine as-is).
- **Engines (already UI-agnostic — your biggest asset):** `database.py` (SQLAlchemy → Supabase Postgres, session pooler :5432), `payment_engine.py` (Stripe), `mailer.py` (PostGrid), `ai_engine.py` (OpenAI Whisper API + Twilio outbound calls), `email_engine.py` (Resend), `heirloom_engine.py`, `bulk_engine.py`, `audit_engine.py`, `letter_format.py` (fpdf2), `secrets_manager.py`.
- **Twilio inbound:** `heirloom-brain/` — Node Twilio Functions hosted at `*.twil.io`, separate from the web app.
- **UI controllers:** `ui_splash`, `ui_login`, `ui_advisor`, `ui_heirloom`, `ui_archive`, `ui_admin`, `ui_legal`, `ui_onboarding`.

### Why Streamlit is slow here

1. **Full-script rerun on every interaction** — every button click re-executes the app and re-renders over a websocket. This is the core, unfixable bottleneck.
2. **Websocket session model** — heavy first paint, poor mobile performance, breaks on idle/reconnect, and forced you to disable CSRF/CORS in the dockerfile.
3. **Fat container** — ffmpeg + all deps in one image = slow Cloud Run cold starts.
4. **No real routing/SEO** — `?nav=` params and `seo_injector.py` hacking Streamlit's HTML are workarounds for missing fundamentals.
5. **Fragile state** — your own changelog is dominated by session-state sync bugs (`addr_to` syncing, rerun loops, audio re-transcription hashes). These are Streamlit-model problems, not code problems.

### Architectural issues to fix during migration (not just speed)

- **Stripe fulfillment on browser redirect** (`?session_id=` in `main.py`): if the user closes the tab after paying, fulfillment never runs — this is why the admin "Repair Station" exists. Must move to **Stripe webhooks**.
- **Transcription/bulk mail run synchronously in the web process** — blocks requests; belongs in background jobs.
- **QR playback URLs (`?play=`) are printed on physical letters** — these must keep working forever.

---

## 2. Target Architecture

```
verbapost.com          → static marketing (unchanged)
app.verbapost.com      → FastAPI on Cloud Run
  GET  /                    splash (Jinja2, real SEO tags — delete seo_injector.py)
  GET  /login /signup       Supabase auth + Google OAuth callback
  GET  /advisor             advisor dashboard (HTMX partials)
  GET  /heirloom            inbox / edit / send
  GET  /archive             heir archive
  GET  /admin               admin console
  GET  /play/{id}           public QR player  (+ keep /?play= as redirect)
  POST /webhooks/stripe     fulfillment (idempotent)
  POST /webhooks/twilio     recording-complete → queue transcription
  GET  /blog/... /legal     server-rendered, indexable
```

- **Stack:** FastAPI + Jinja2 + HTMX (+ Alpine.js for small client-side bits, Tailwind for styling). 100% Python; all engines port with minimal changes.
- **Auth:** keep Supabase auth. Store the Supabase JWT in a signed, HttpOnly cookie (Starlette `SessionMiddleware`). Cookie on `.verbapost.com` so old and new services share login during migration.
- **DB:** keep `database.py` + SQLAlchemy sync (FastAPI runs sync routes in a threadpool — no async rewrite needed). Keep pooler :5432; set `pool_size`/`max_overflow` explicitly.
- **Background work:** start with FastAPI `BackgroundTasks` for transcription; move bulk campaigns to Cloud Tasks → a `/tasks/...` endpoint if volume grows.
- **Container:** `python:3.12-slim`, no ffmpeg (Whisper is via OpenAI API now), `uvicorn --workers 2`. Image drops from ~1.5GB-class to ~200MB → fast cold starts. Optionally `min-instances=1` (~$10/mo) to eliminate them.
- **Secrets:** keep `secrets_manager.py` env-var path; move keys into GCP Secret Manager referenced by Cloud Run.

**What this buys you:** page loads go from multi-second websocket reruns to ~100–300ms server-rendered responses; every click no longer re-executes the app; real URLs, real SEO, CSRF back on, and the whole class of session-state bugs disappears.

---

## 3. Migration Phases

### Phase 0 — Safety net (1–2 days)
- Pin `requirements.txt` versions; branch `fastapi-migration`.
- Expand `tests/` around the engines (payment, mailer, letter_format, database) — these are the contract both UIs share.
- Scaffold `app/` (FastAPI, templates, static) in the same repo so engines import directly. Deploy skeleton to Cloud Run as `verbapost-web` at `beta.verbapost.com`.
- Set up staging + CI/CD (see Section 6): `verbapost-web-staging` service, GitHub Actions deploy workflows, `ENV` variable + staging banner.

### Phase 1 — Backend wins that don't touch the UI (2–3 days)
Ship these while Streamlit is still the frontend — immediate reliability gains:
1. **Stripe webhook** (`checkout.session.completed`) → fulfillment via existing `payment_engine` + `mailer`, idempotent on session ID. Keep the redirect handler as a UX confirmation only.
2. **Twilio recording-status callback** → download recording, transcribe, save draft. Kills the "Check for New Stories" manual polling.
3. **`/play/{id}` public player** — plus permanent redirect support for legacy `?play=` links (QR codes already in the mail).

### Phase 2 — Public pages + auth (3–5 days)
- Splash, legal, blog, login/signup/password-reset, Google OAuth callback.
- Proper meta tags, sitemap, robots — retire `seo_injector.py`.

### Phase 3 — Core product flows (1–2 weeks)
- **Advisor dashboard** (`ui_advisor` → templates + HTMX partials).
- **Heirloom inbox/edit/send**: HTMX inline editing; PDF preview served as a real `/letters/{id}/preview.pdf` response instead of base64-in-page (this alone is a huge perf win).
- **Checkout**: server-side price calc (`pricing_engine`), Stripe session, webhook fulfillment. Preserve the promo-code `total <= 0` path (record usage, skip Stripe).
- Bulk/campaign CSV flow via background task.

### Phase 4 — Admin console (3–4 days)
- Health checks, order manager (merge `letters` + `letter_drafts`), Repair Station, audit log viewer. Straight port; HTMX tables.

### Phase 5 — Cutover (1 day + 1 week observation)
1. Full end-to-end test on `beta.verbapost.com` including one real $ transaction.
2. Point `app.verbapost.com` DNS at the new service; keep Streamlit live at `legacy.verbapost.com` for a week as fallback.
3. Watch `audit_events` + Cloud Run logs; then decommission the Streamlit service and delete `ui_*.py`.

**Total: roughly 4–6 weeks part-time; each phase ships independently.** (Revised to ~1.5–2 weeks with Claude writing the code and single revision-swap cutover — see Phase 5 note.)

### Regression protection (applies to every phase)

1. **Port only — no new features until after cutover.** The migration reproduces current behavior exactly. New feature ideas go in the Parking Lot below.
2. **Cumulative test suite.** Each phase adds TestClient tests for its routes (mocked Stripe/PostGrid/Twilio). CI runs the full suite on every push — later phases cannot silently break earlier ones.
3. **One phase = one PR.** Reviewable diffs, revertible in isolation.
4. **Final sweep.** One complete manual pass on staging (including a real Stripe test payment and a live Twilio test call) before the prod revision swap — the only manual regression pass in the whole project.

### Parking Lot (post-migration features)
- Voice-to-USPS letter vending machine (PostcardMania/PCM integration groundwork already in env vars)

### Phase 5 cutover checklist additions (learned on staging)
- PROD Supabase → Authentication → URL Configuration: Site URL must be `https://app.verbapost.com`, Redirect URLs `https://app.verbapost.com/**` (staging shipped with default localhost:3000 and broke confirmation-email redirects).
- Set `--no-cpu-throttling` on `verbapost-app` at cutover: FastAPI background tasks (webhook fulfillment, transcription) freeze under Cloud Run's default request-only CPU. Staging already runs this way.
- stripe-python v15 removed `.get()` on Stripe objects — fixed via `_sget` in payment_engine (would also have hit prod on any container rebuild).

### Phase 5 (revised) — Cutover via revision swap
All three domains already map to `verbapost-app`, so cutover requires **no DNS changes**: deploy the FastAPI image as a new revision of the existing service. Rollback = `gcloud run services update-traffic verbapost-app --to-revisions=STREAMLIT_REVISION=100` (~10 seconds). Streamlit stays one revision back as the safety net; no parallel running needed.

---

## 4. Risks & Gotchas

| Risk | Mitigation |
|---|---|
| QR codes on printed letters break | `/play/{id}` + permanent `?play=` redirect; test before cutover |
| Stripe redirect URLs in flight at cutover | Keep `?session_id=` handler in new app; webhooks make it moot |
| Double fulfillment (webhook + redirect) | Idempotency key on Stripe session ID in DB (partially exists — "Already Fulfilled") |
| Supabase pooler exhaustion | Session pooler :5432, explicit pool sizing, one engine instance per worker |
| Python 3.9 → 3.12 surprises | Engines are simple; run test suite on 3.12 in Phase 0 |
| Twilio Functions (`heirloom-brain`) drift | Leave as-is initially; optionally fold into FastAPI `/webhooks/twilio` later so all logic lives in one repo |
| AI-assistant workflow (AI_RULES.md) | Update AI_RULES for the new structure; template-per-page + engine files keeps the "full file replacement" workflow viable |

---

## 5. Suggested new layout

```
VerbaPost-Live/
├── app/
│   ├── main.py            # FastAPI app, middleware, routers
│   ├── routers/           # splash, auth, advisor, heirloom, admin, webhooks, play
│   ├── templates/         # Jinja2 (base.html + per-page + HTMX partials)
│   └── static/            # css, js, fonts, images
├── engines/               # existing *_engine.py, mailer.py, database.py, letter_format.py (moved, unchanged)
├── heirloom-brain/        # Twilio Functions (unchanged for now)
├── tests/
├── dockerfile             # python:3.12-slim + uvicorn
└── requirements.txt       # fastapi, uvicorn, jinja2, python-multipart, itsdangerous + existing deps (minus streamlit)
```

## 6. Staging Environment & CI/CD

Today: QA on Streamlit Cloud, prod on Cloud Run, manual `gcloud` deploys, and a test-only GitHub Action (`verify_hardening.yml`). The new setup replaces Streamlit Cloud QA with a second Cloud Run service — same container as prod, different config.

### Environments

| | Service | URL | Branch | Keys |
|---|---|---|---|---|
| Staging | `verbapost-web-staging` | `staging.verbapost.com` | `staging` | Stripe **test**, PostGrid test, staging DB |
| Prod | `verbapost-web` | `app.verbapost.com` (after cutover) | `main` | Live keys (unchanged) |

- **Config, not code:** `secrets_manager.py` already reads env vars, so both services run the identical image. Add one new var, `ENV` (`staging`/`production`).
- **Staging banner:** `base.html` shows a colored "STAGING" bar when `ENV=staging` — impossible to confuse the two.
- **Database:** simplest is a second free-tier Supabase project for staging (clean separation of auth users too). Copy schema with `supabase db dump` / restore.
- **Webhooks in staging:** point a Stripe test-mode webhook endpoint at `staging.verbapost.com/webhooks/stripe`; Twilio test creds for the recording callback.

### CI/CD (GitHub Actions)

Two new workflows alongside the existing test workflow:

1. `deploy-staging.yml` — on push to `staging`: run tests → build with Cloud Build → deploy to `verbapost-web-staging`.
2. `deploy-prod.yml` — on push to `main` (or a version tag): same, deploying to `verbapost-web`. Optionally gated by a GitHub "environment" approval click.

Auth via a GCP service account key (simple) or Workload Identity Federation (better, no long-lived key). Rollback is built into Cloud Run: `gcloud run services update-traffic verbapost-web --to-revisions=PREV=100`.

### Preview revisions (bonus)

For risky changes, deploy to staging with `--tag pr-42 --no-traffic` → gets a private URL like `pr-42---verbapost-web-staging-xxxx.run.app` without touching staging itself.

### Local dev

`uvicorn app.main:app --reload` with a `.env` file (staging keys) — sub-second template reload, replaces much of what Streamlit Cloud QA was used for.

---

## 7. GCP Inventory (verified July 2026)

| Item | Value |
|---|---|
| Project | `verbapost-prod` |
| Region | `us-central1` |
| Prod service | `verbapost-app` — 1 vCPU / 2 GiB, maxScale 5, startup CPU boost, deployed from source (`cloud-run-source-deploy` Artifact Registry repo) |
| Domain mappings | `verbapost.com`, `www.verbapost.com`, **and** `app.verbapost.com` all → `verbapost-app` |

**Key finding:** all three domains point at the single Streamlit service — the marketing site is served by the Streamlit container (via `STREAMLIT_SERVER_ENABLE_STATIC_SERVING` + `verbapost-marketing/index.html`). So the cutover isn't just `app.` — the new FastAPI service must also serve the marketing page (trivial: mount it as a static route or serve `index.html` at `/` for the apex domain), and all three domain mappings move together. The upside: marketing-page loads currently pay Streamlit's startup cost too, so the speedup will be visible on verbapost.com itself.

**Env vars to replicate on staging (same names, test values):**
`BASE_URL, SUPABASE_URL, SUPABASE_KEY, DATABASE_URL, ADMIN_EMAIL, POSTGRID_API_KEY, GEOCODIO_API_KEY, RESEND_API_KEY, STRIPE_SECRET_KEY, STRIPE_PUBLISHABLE_KEY, OPENAI_API_KEY, GA_ID, ADMIN_PASSWORD, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, PCM_API_KEY, PCM_BASE_URL, PCM_API_SECRET, EMAIL_SENDER` + new `ENV=staging`.

Notes:
- `admin.password` has a dot in the name (not POSIX-valid; some tooling chokes on it) — rename to `ADMIN_PASSWORD` in the new app and update `secrets_manager.py` lookups.
- `STREAMLIT_SERVER_ENABLE_STATIC_SERVING` is dropped (FastAPI serves static natively).
- Staging service: `verbapost-web-staging`, 1 vCPU / 512 MiB–1 GiB (FastAPI needs far less than 2 GiB), maxScale 2.

## 8. First concrete step

Phase 0 + Phase 1.1 (Stripe webhook) is the highest-value starting point: it fixes your most serious reliability bug before any UI work begins, and it stands up the FastAPI service you'll build everything else on.
