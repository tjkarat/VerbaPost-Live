"""
Phase 0 scaffold tests — run with:  python -m pytest tests/test_app_scaffold.py -v

These are the first bricks of the cumulative regression suite:
every later phase adds tests here, and CI runs ALL of them on every push.
"""

import os
import sys
from pathlib import Path

# Make repo root importable regardless of where pytest is invoked from
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("ENV", "staging")  # exercise the staging banner path

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_splash_renders():
    r = client.get("/")
    assert r.status_code == 200
    assert "VerbaPost" in r.text
    assert "Family Legacy Archive" in r.text


def test_staging_banner_present_in_staging_env():
    r = client.get("/")
    assert "STAGING ENVIRONMENT" in r.text


def test_legacy_qr_play_link_redirects():
    """QR codes printed on already-mailed letters use /?play=<id>.
    They MUST keep working forever."""
    r = client.get("/?play=abc123", follow_redirects=False)
    assert r.status_code == 301
    assert r.headers["location"] == "/play/abc123"


def test_play_route_resolves():
    # "demo" is the built-in sample story; unknown IDs correctly 404
    # (covered in test_phase1_webhooks.py).
    r = client.get("/play/demo")
    assert r.status_code == 200


def test_legacy_nav_param_redirects():
    """Marketing site links use /?nav=login etc."""
    r = client.get("/?nav=login", follow_redirects=False)
    assert r.status_code == 301
    assert r.headers["location"] == "/login"


def test_known_stub_page_returns_200():
    r = client.get("/login")
    assert r.status_code == 200


def test_unknown_page_returns_404():
    r = client.get("/definitely-not-a-page")
    assert r.status_code == 404


def test_robots_and_sitemap_served():
    assert client.get("/robots.txt").status_code == 200
    assert client.get("/sitemap.xml").status_code == 200
