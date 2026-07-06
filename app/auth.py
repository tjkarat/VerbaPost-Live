"""
Authentication routes — Phase 2.

Wraps the existing auth_engine (Supabase) with server-side session cookies.

GET  /login           login / signup / forgot-password page
POST /login           email+password sign in
POST /signup          create account (Supabase sends confirmation email)
POST /forgot          send password-reset email (OTP)
GET  /reset           reset form (email + code + new password)
POST /reset           verify OTP and set new password
GET  /auth/google     redirect to Google OAuth (PKCE)
GET  /auth/callback   Google redirects back here with ?code=
GET  /logout          clear session
"""

import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

import auth_engine
import database

logger = logging.getLogger(__name__)
router = APIRouter()


def _base_url() -> str:
    return os.environ.get("BASE_URL", "http://localhost:8000").rstrip("/")


def _login_user(request: Request, email: str):
    """Set the session cookie and return the role-appropriate landing path."""
    email = (email or "").strip().lower()
    profile = database.get_user_profile(email) or {}
    role = profile.get("role", "user")
    request.session["email"] = email
    request.session["role"] = role
    request.session["name"] = profile.get("full_name") or email
    admin_email = (os.environ.get("ADMIN_EMAIL") or "").strip().lower()
    if email == admin_email:
        request.session["role"] = "admin"
        return "/admin"
    if role == "advisor":
        return "/advisor"
    return "/heirloom"


def current_user(request: Request):
    """Helper for other routers: returns session email or None."""
    return request.session.get("email")


# ---------- Pages ----------

def _render_login(request: Request, **ctx):
    from app.main import templates
    base = {"error": None, "notice": None, "active_tab": "login"}
    base.update(ctx)
    return templates.TemplateResponse(request, "login.html", base)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if request.session.get("email"):
        return RedirectResponse("/advisor" if request.session.get("role") == "advisor"
                                else "/heirloom", status_code=302)
    return _render_login(request)


@router.post("/login", response_class=HTMLResponse)
def login_submit(request: Request, email: str = Form(...), password: str = Form(...)):
    user, err = auth_engine.sign_in(email, password)
    if not user:
        logger.info(f"Login failed for {email}: {err}")
        return _render_login(request, error="Invalid email or password.", shake=True)
    dest = _login_user(request, email)
    return RedirectResponse(dest, status_code=302)


@router.post("/signup", response_class=HTMLResponse)
def signup_submit(request: Request, email: str = Form(...), password: str = Form(...),
                  full_name: str = Form("")):
    if len(password) < 8:
        return _render_login(request, error="Password must be at least 8 characters.",
                             active_tab="signup", shake=True)
    user, err = auth_engine.sign_up(email, password, data={"full_name": full_name})
    if not user:
        return _render_login(request, error=f"Signup failed: {err}", active_tab="signup", shake=True)
    database.create_user(email, full_name)
    return _render_login(
        request, active_tab="login",
        notice="Account created. Check your email for a confirmation link, then log in.")


@router.post("/forgot", response_class=HTMLResponse)
def forgot_submit(request: Request, email: str = Form(...)):
    ok, err = auth_engine.send_password_reset(email)
    # Always show the same message — don't leak which emails exist.
    return _render_login(
        request, active_tab="login",
        notice="If that email has an account, a reset code is on its way. "
               "Use it on the reset page.",
        reset_link=True)


@router.get("/reset", response_class=HTMLResponse)
def reset_page(request: Request):
    from app.main import templates
    return templates.TemplateResponse(request, "reset.html", {"error": None})


@router.post("/reset", response_class=HTMLResponse)
def reset_submit(request: Request, email: str = Form(...), token: str = Form(...),
                 new_password: str = Form(...)):
    from app.main import templates
    if len(new_password) < 8:
        return templates.TemplateResponse(
            request, "reset.html", {"error": "Password must be at least 8 characters."})
    session, err = auth_engine.verify_otp(email, token.strip(), type="recovery")
    if not session:
        return templates.TemplateResponse(
            request, "reset.html", {"error": f"Invalid or expired code. ({err})"})
    ok, err = auth_engine.update_user_password(new_password)
    if not ok:
        return templates.TemplateResponse(
            request, "reset.html", {"error": f"Could not update password: {err}"})
    return _render_login(request, notice="Password updated. Log in with your new password.")


# ---------- Google OAuth (PKCE) ----------

@router.get("/auth/google")
def google_start():
    url = auth_engine.get_oauth_url(provider="google",
                                    redirect_to=f"{_base_url()}/auth/callback")
    if not url:
        return RedirectResponse("/login", status_code=302)
    return RedirectResponse(url, status_code=302)


@router.get("/auth/callback")
def google_callback(request: Request, code: str = ""):
    if not code:
        return RedirectResponse("/login", status_code=302)
    user, err = auth_engine.exchange_code_for_user(code)
    if not user:
        logger.error(f"OAuth exchange failed: {err}")
        return RedirectResponse("/login?oauth=failed", status_code=302)
    dest = _login_user(request, user.email)
    return RedirectResponse(dest, status_code=302)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=302)
