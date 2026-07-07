"""
VerbaPost — FastAPI application (Phase 0 scaffold).

This app runs ALONGSIDE the Streamlit app (repo-root main.py) during the
migration. Nothing here touches production until the Phase 5 revision swap.

Run locally:
    uvicorn app.main:app --reload
Then open http://localhost:8000

Environment:
    ENV             development | staging | production  (default: development)
    SESSION_SECRET  random string for signing session cookies (required in prod)
"""

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

# --- Paths ---
APP_DIR = Path(__file__).resolve().parent          # .../app
REPO_ROOT = APP_DIR.parent                          # repo root (engines live here)
STATIC_DIR = REPO_ROOT / "static"                   # existing fonts/images/robots
TEMPLATES_DIR = APP_DIR / "templates"

# --- Config ---
ENV = os.environ.get("ENV", "development")

app = FastAPI(title="VerbaPost", docs_url=None, redoc_url=None)

# Signed session cookie (replaces Streamlit session_state for auth in Phase 2)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET", "dev-only-secret-not-for-production"),
    https_only=(ENV != "development"),
    same_site="lax",
)

# Existing repo static assets (fonts, social previews, robots.txt, sitemap.xml)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["ENV"] = ENV  # lets base.html show the STAGING banner


# ============================================================
# Health & SEO plumbing
# ============================================================

@app.get("/health")
def health():
    """Used by Cloud Run and the deploy workflows to verify the app booted."""
    return {"status": "ok", "env": ENV}


@app.get("/robots.txt", include_in_schema=False)
def robots():
    return FileResponse(STATIC_DIR / "robots.txt")


@app.get("/sitemap.xml", include_in_schema=False)
def sitemap():
    return FileResponse(STATIC_DIR / "sitemap.xml")


# ============================================================
# Pages
# ============================================================

@app.get("/", response_class=HTMLResponse)
def splash(request: Request):
    # LEGACY QR LINKS: letters already in the mail carry
    # https://app.verbapost.com/?play=<id> — redirect them to the new route.
    play_id = request.query_params.get("play")
    if play_id:
        return RedirectResponse(url=f"/play/{play_id}", status_code=301)

    # LEGACY NAV LINKS: marketing site links use ?nav=login / ?nav=advisor etc.
    nav = request.query_params.get("nav")
    if nav:
        return RedirectResponse(url=f"/{nav}", status_code=301)

    # LEGACY GOOGLE OAUTH: old flow redirected to / with ?code=
    code = request.query_params.get("code")
    if code:
        return RedirectResponse(url=f"/auth/callback?code={code}", status_code=302)

    # STRIPE RETURN SAFETY NET: any checkout session that still lands on the
    # root (old success URLs in flight) belongs in the advisor portal.
    # Fulfillment itself is handled by the webhook — this is purely UX.
    if request.query_params.get("session_id"):
        return RedirectResponse(url="/advisor?purchased=1", status_code=302)

    return templates.TemplateResponse(request, "splash.html", {})


# ============================================================
# Feature routers (Phase 1+). Registered BEFORE the /{page}
# catch-all below so their routes take precedence.
# ============================================================

from app.advisor import router as advisor_router    # noqa: E402
from app.auth import router as auth_router          # noqa: E402
from app.heirloom import router as heirloom_router  # noqa: E402
from app.pages import router as pages_router        # noqa: E402
from app.player import router as player_router      # noqa: E402
from app.webhooks import router as webhooks_router  # noqa: E402

app.include_router(auth_router)      # /login /signup /forgot /reset /auth/* /logout
app.include_router(advisor_router)   # /advisor dashboard + actions + checkout
app.include_router(heirloom_router)  # /heirloom dashboard + /archive/{pid}
app.include_router(pages_router)     # /legal /blog /blog/{slug}
app.include_router(player_router)    # /play/{id}, /play/{id}/audio.mp3
app.include_router(webhooks_router)  # /webhooks/stripe, /webhooks/twilio/recording


@app.get("/archive")
def archive_root():
    """Old nav link (?nav=archive). Heirs see their stories after logging in."""
    return RedirectResponse("/heirloom", status_code=302)


@app.get("/{page}", response_class=HTMLResponse)
def stub_pages(request: Request, page: str):
    """Placeholder for pages arriving in Phases 2-4 (login, advisor, heirloom,
    admin, legal, archive...). Returns a friendly 'coming soon' rather than 404
    so navigation links in templates stay real from day one."""
    # Only admin (Phase 4) and help remain as stubs; everything else is real.
    known = {"admin", "help"}
    if page not in known:
        return templates.TemplateResponse(
            request, "coming_soon.html",
            {"title": "Page not found", "detail": ""}, status_code=404,
        )
    return templates.TemplateResponse(
        request, "coming_soon.html",
        {"title": page.capitalize(), "detail": "This page is being migrated to the new platform."},
    )
