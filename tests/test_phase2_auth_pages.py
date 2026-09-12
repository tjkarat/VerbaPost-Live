"""
Phase 2 regression tests: auth flows (mocked Supabase), legal, blog.
Run:  python -m pytest tests/test_phase2_auth_pages.py -v
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("ENV", "staging")
os.environ.setdefault("BASE_URL", "https://staging.verbapost.com")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


# ============================================================
# 🔐 Login / logout
# ============================================================

def test_login_page_renders():
    r = client.get("/login")
    assert r.status_code == 200
    assert "Log in" in r.text
    assert "Continue with Google" in r.text


def test_login_success_sets_session_and_redirects():
    fake_user = MagicMock()
    with patch("app.auth.auth_engine.sign_in", return_value=(fake_user, None)), \
         patch("app.auth.database.get_user_profile",
               return_value={"role": "advisor", "full_name": "Test Advisor"}):
        # https base_url: session cookies are Secure-only outside development,
        # so the client must speak HTTPS for the cookie to round-trip.
        c = TestClient(app, base_url="https://testserver")
        r = c.post("/login", data={"email": "adv@test.com", "password": "pw12345678"},
                   follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/advisor"
        # session cookie now present; a second request keeps the login
        r2 = c.get("/login", follow_redirects=False)
        assert r2.status_code == 302  # already logged in -> bounced to app


def test_login_failure_shows_error_and_shake():
    with patch("app.auth.auth_engine.sign_in", return_value=(None, "Invalid login")):
        r = client.post("/login", data={"email": "x@y.com", "password": "wrong1234"})
        assert r.status_code == 200
        assert "Invalid email or password" in r.text
        assert "shake" in r.text  # the beloved shake animation survives the migration


def test_heir_lands_on_heirloom():
    fake_user = MagicMock()
    with patch("app.auth.auth_engine.sign_in", return_value=(fake_user, None)), \
         patch("app.auth.database.get_user_profile", return_value={"role": "heir"}):
        r = client.post("/login", data={"email": "heir@test.com", "password": "pw12345678"},
                        follow_redirects=False)
        assert r.headers["location"] == "/heirloom"


def test_admin_email_lands_on_admin():
    fake_user = MagicMock()
    with patch("app.auth.auth_engine.sign_in", return_value=(fake_user, None)), \
         patch("app.auth.database.get_user_profile", return_value={"role": "user"}), \
         patch.dict(os.environ, {"ADMIN_EMAIL": "boss@verbapost.com"}):
        r = client.post("/login", data={"email": "boss@verbapost.com", "password": "pw12345678"},
                        follow_redirects=False)
        assert r.headers["location"] == "/admin"


def test_logout_clears_session():
    fake_user = MagicMock()
    with patch("app.auth.auth_engine.sign_in", return_value=(fake_user, None)), \
         patch("app.auth.database.get_user_profile", return_value={"role": "advisor"}):
        c = TestClient(app, base_url="https://testserver")
        c.post("/login", data={"email": "a@b.com", "password": "pw12345678"})
        # confirm the login actually stuck before testing logout
        assert c.get("/login", follow_redirects=False).status_code == 302
        r = c.get("/logout", follow_redirects=False)
        assert r.status_code == 302
        r2 = c.get("/login")
        assert r2.status_code == 200  # not bounced -> session is gone


# ============================================================
# 📝 Signup / forgot / reset
# ============================================================

def test_signup_success_shows_confirmation_notice():
    fake_user = MagicMock()
    with patch("app.auth.auth_engine.sign_up", return_value=(fake_user, None)), \
         patch("app.auth.database.create_user", return_value=True):
        r = client.post("/signup", data={"email": "new@test.com",
                                         "password": "longenough", "full_name": "New User"})
        assert r.status_code == 200
        assert "Check your email" in r.text


def test_signup_short_password_rejected_without_calling_supabase():
    with patch("app.auth.auth_engine.sign_up") as mock_signup:
        r = client.post("/signup", data={"email": "new@test.com",
                                         "password": "short", "full_name": ""})
        assert "at least 8 characters" in r.text
        mock_signup.assert_not_called()


def test_forgot_never_leaks_account_existence():
    with patch("app.auth.auth_engine.send_password_reset", return_value=(False, "no user")):
        r = client.post("/forgot", data={"email": "ghost@test.com"})
        assert r.status_code == 200
        assert "If that email has an account" in r.text  # same message either way


def test_reset_with_valid_code_updates_password():
    with patch("app.auth.auth_engine.verify_otp", return_value=(MagicMock(), None)), \
         patch("app.auth.auth_engine.update_user_password", return_value=(True, None)):
        r = client.post("/reset", data={"email": "a@b.com", "token": "123456",
                                        "new_password": "newpass123"})
        assert "Password updated" in r.text


def test_reset_with_bad_code_shows_error():
    with patch("app.auth.auth_engine.verify_otp", return_value=(None, "expired")):
        r = client.post("/reset", data={"email": "a@b.com", "token": "000000",
                                        "new_password": "newpass123"})
        assert "Invalid or expired code" in r.text


def test_recovery_link_flow_updates_password():
    """Supabase reset emails deliver tokens in the URL fragment; the recovery
    page moves them into a POST and the engine sets the new password."""
    r = client.get("/auth/recovery")
    assert r.status_code == 200
    assert "Set a new password" in r.text
    with patch("app.auth.auth_engine.complete_recovery",
               return_value=("a@b.com", None)) as mock_rec:
        r = client.post("/auth/recovery",
                        data={"access_token": "tok123", "refresh_token": "ref456",
                              "new_password": "newpass123"})
        assert "Password updated" in r.text
        mock_rec.assert_called_once_with("tok123", "ref456", "newpass123")


def test_recovery_with_expired_token_shows_error():
    with patch("app.auth.auth_engine.complete_recovery",
               return_value=(None, "token expired")):
        r = client.post("/auth/recovery",
                        data={"access_token": "old", "refresh_token": "",
                              "new_password": "newpass123"})
        assert "invalid or expired" in r.text


# ============================================================
# 🔗 Google OAuth
# ============================================================

def test_google_start_redirects_to_provider():
    with patch("app.auth.auth_engine.get_oauth_url",
               return_value="https://supabase.example/oauth?x=1") as mock_url:
        r = client.get("/auth/google", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"].startswith("https://supabase.example/oauth")
        # callback must point at our /auth/callback
        assert mock_url.call_args.kwargs["redirect_to"].endswith("/auth/callback")


def test_google_callback_logs_user_in():
    fake_user = MagicMock()
    fake_user.email = "google@test.com"
    with patch("app.auth.auth_engine.exchange_code_for_user", return_value=(fake_user, None)), \
         patch("app.auth.database.get_user_profile", return_value={"role": "advisor"}):
        r = client.get("/auth/callback?code=pkce123", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/advisor"


def test_legacy_root_code_param_redirects_to_callback():
    r = client.get("/?code=legacy123", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/auth/callback?code=legacy123"


# ============================================================
# 📜 Legal & blog
# ============================================================

def test_legal_page_renders_key_terms():
    r = client.get("/legal")
    assert r.status_code == 200
    assert "NOT A LEGAL DOCUMENT" in r.text
    # The window the Terms promise must be the window the purge job enforces.
    # Asserting the literal number would only prove the page still says what it
    # said; asserting against RETENTION_DAYS makes the two impossible to drift.
    from app.player import RETENTION_DAYS
    assert f"{RETENTION_DAYS}-DAY ACTIVE WINDOW" in r.text
    assert f"<strong>{RETENTION_DAYS} days</strong>" in r.text


def test_blog_index_lists_posts():
    r = client.get("/blog")
    assert r.status_code == 200
    assert "Welcome to the VerbaPost Blog" in r.text


def test_blog_post_renders():
    r = client.get("/blog/welcome")
    assert r.status_code == 200
    assert "greenway" in r.text.lower()


def test_blog_unknown_slug_404s():
    r = client.get("/blog/does-not-exist")
    assert r.status_code == 404
