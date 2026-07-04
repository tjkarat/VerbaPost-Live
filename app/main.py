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

    return templates.TemplateResponse(request, "splash.html", {})


@app.get("/play/{audio_id}", response_class=HTMLResponse)
def public_player(request: Request, audio_id: str):
    """Public QR-code audio player.

    Phase 1 replaces this placeholder with the real player
    (port of ui_heirloom.render_public_player). The route exists now so
    QR links printed on mailed letters resolve on the new stack.
    """
    return templates.TemplateResponse(
        request, "coming_soon.html",
        {"title": "Family Archive Player", "detail": f"Audio story {audio_id}"},
    )


@app.get("/{page}", response_class=HTMLResponse)
def stub_pages(request: Request, page: str):
    """Placeholder for pages arriving in Phases 2-4 (login, advisor, heirloom,
    admin, legal, archive...). Returns a friendly 'coming soon' rather than 404
    so navigation links in templates stay real from day one."""
    known = {"login", "signup", "advisor", "heirloom", "archive", "admin", "legal", "help", "blog"}
    if page not in known:
        return templates.TemplateResponse(
            request, "coming_soon.html",
            {"title": "Page not found", "detail": ""}, status_code=404,
        )
    return templates.TemplateResponse(
        request, "coming_soon.html",
        {"title": page.capitalize(), "detail": "This page is being migrated to the new platform."},
    )
