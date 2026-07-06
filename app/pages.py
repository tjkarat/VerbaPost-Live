"""
Public content pages — Phase 2: /legal, /blog, /blog/{slug}.
Blog posts are the markdown files in blog_posts/ (title = first heading).
"""

import logging
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

logger = logging.getLogger(__name__)
router = APIRouter()

BLOG_DIR = Path(__file__).resolve().parent.parent / "blog_posts"

try:
    import markdown as _md

    def _md_to_html(text: str) -> str:
        return _md.markdown(text, extensions=["extra"])
except ImportError:  # crude fallback so the page still renders
    def _md_to_html(text: str) -> str:
        html = text
        html = re.sub(r"^### (.*)$", r"<h3>\1</h3>", html, flags=re.M)
        html = re.sub(r"^## (.*)$", r"<h2>\1</h2>", html, flags=re.M)
        html = re.sub(r"^# ?(.*)$", r"<h1>\1</h1>", html, flags=re.M)
        html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
        html = re.sub(r"^> (.*)$", r"<blockquote>\1</blockquote>", html, flags=re.M)
        return "".join(f"<p>{p}</p>" if not p.strip().startswith("<") else p
                       for p in html.split("\n\n"))


def _slug(filename: str) -> str:
    stem = Path(filename).stem                    # "01_welcome"
    return re.sub(r"^\d+[_-]?", "", stem) or stem  # "welcome"


def _title_of(text: str, fallback: str) -> str:
    for line in text.splitlines():
        m = re.match(r"^#\s*(.+)$", line.strip())
        if m:
            return m.group(1).strip()
    return fallback


def list_posts():
    posts = []
    if BLOG_DIR.is_dir():
        for f in sorted(BLOG_DIR.glob("*.md"), reverse=True):
            try:
                text = f.read_text(encoding="utf-8")
            except OSError:
                continue
            posts.append({
                "slug": _slug(f.name),
                "title": _title_of(text, _slug(f.name).replace("-", " ").title()),
                "preview": re.sub(r"[#*>`]", "", text).strip()[:180] + "…",
            })
    return posts


def load_post(slug: str):
    if not BLOG_DIR.is_dir():
        return None
    for f in BLOG_DIR.glob("*.md"):
        if _slug(f.name) == slug:
            text = f.read_text(encoding="utf-8")
            title = _title_of(text, slug)
            # Remove the first heading; template renders the title itself
            body = re.sub(r"^#\s*.+\n", "", text, count=1)
            return {"slug": slug, "title": title, "html": _md_to_html(body)}
    return None


@router.get("/blog", response_class=HTMLResponse)
def blog_index(request: Request):
    from app.main import templates
    return templates.TemplateResponse(request, "blog_index.html", {"posts": list_posts()})


@router.get("/blog/{slug}", response_class=HTMLResponse)
def blog_post(request: Request, slug: str):
    from app.main import templates
    post = load_post(slug)
    if not post:
        return templates.TemplateResponse(
            request, "coming_soon.html",
            {"title": "Post not found", "detail": ""}, status_code=404)
    return templates.TemplateResponse(request, "blog_post.html", {"post": post})


@router.get("/legal", response_class=HTMLResponse)
def legal(request: Request):
    from app.main import templates
    return templates.TemplateResponse(request, "legal.html", {})
