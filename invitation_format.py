"""
Invitation letter — the direct-mail piece that replaces the free-dinner
seminar invite. One page, mailed to every name on the advisor's uploaded
list. Each copy carries that person's OWN link and QR (/a/{slug}/i/{token})
so the response can be attributed to the mailing.

ADDRESS PLACEMENT: PostGrid overlays the recipient/return address onto the
top of page one for a #10 double-window envelope (the PostGrid rule in
AI_RULES.md), so a PostGrid send needs BODY_START_Y left blank. PCM instead
generates and inserts its OWN address page ahead of this artwork
(insertAddressingPage + envelope.type=fullWindow), so a PCM send should NOT
reserve that blank zone -- confirmed against a real Sandbox order, where the
reserved space just left an empty top half of the letter with nothing to
show through it. create_invitation_pdf(compact=True) starts the letterhead
near the top of the page instead; campaign_engine picks it automatically
based on which mail provider is active.
"""

import logging
import os
import tempfile
from datetime import datetime

import qrcode
from fpdf import FPDF

logger = logging.getLogger(__name__)

PAGE_W = 215.9
PAGE_H = 279.4
MARGIN = 25.4            # 1 inch
BODY_START_Y = 115.0     # PostGrid address safe zone (see AI_RULES.md)
BODY_START_Y_COMPACT = 20.0  # PCM: it inserts its own address page, so this
                             # page can start near the top (still below MARGIN)

DEFAULT_INVITE_BODY = (
    "I'd like to give you something that has nothing to do with money.\n\n"
    "Think of one person who matters to you: a child, a grandchild, a friend. "
    "Now think of one story you'd want them to have in your own words. "
    "When you have a quiet ten minutes, visit the link below and we'll call you right then. Talk for a few minutes. "
    "We'll turn what you say into a letter on linen paper, with a small code they can scan to hear your voice, "
    "and mail it to them. There is no cost, and no obligation of any kind.\n\n"
    "I offer this because the families I work with tell me the same thing: what they wish they had more of "
    "isn't paperwork. It's the voices."
)

# --- the sample story bound into the mailer -------------------------------
# A prospect who can read a finished letter understands the offer in a way no
# description achieves. Leave SAMPLE_STORY empty and the mailer stays one page;
# fill it and the finished letter is bound in behind the invitation, rendered
# by letter_format's own header code so the sample always matches the real
# product.
#
# Paste the transcript of a story you are happy to put in front of strangers.
SAMPLE_STORY = ""
SAMPLE_STORYTELLER = "Tarak R."
SAMPLE_PROMPT = ""          # the question that was asked, shown as the epigraph
SAMPLE_NOTE = ("This is a real letter, printed exactly as yours would be. "
               "The code on it plays the storyteller's own voice.")

_INVITE_VERSION = "invite-v2"


def _sanitize(text):
    if not text:
        return ""
    text = str(text)
    for a, b in {"‘": "'", "’": "'", "“": '"', "”": '"',
                 "–": "-", "—": "--", "…": "..."}.items():
        text = text.replace(a, b)
    return text.encode("latin-1", "replace").decode("latin-1")


def _load_serif(pdf):
    """Use the repo's typewriter face when present (matches the story
    letters); Times otherwise. Returns the family name to use."""
    for path in (os.path.join("assets", "fonts", "type_right.ttf"), "type_right.ttf"):
        if os.path.exists(path):
            try:
                pdf.add_font("TypeRight", "", path)
                return "TypeRight"
            except Exception:
                break
    return "Times"


def create_invitation_pdf(first_name, personal_url, advisor_name, firm_name=None,
                          body=None, disclosure=None, date=None, compact=False,
                          include_sample=True):
    """
    Returns PDF bytes for one invitation. Never raises: on failure returns
    None so the caller marks the row failed instead of mailing garbage.

    compact: True when the mail provider inserts its own address page (PCM)
    so this page shouldn't waste its top third on a blank overlay zone meant
    for a provider (PostGrid) that prints the address onto this artwork
    directly. campaign_engine sets this from mailer.get_mail_provider().
    """
    try:
        pdf = FPDF(orientation="P", unit="mm", format="Letter")
        pdf.set_auto_page_break(auto=False)
        pdf.set_margins(MARGIN, MARGIN, MARGIN)
        pdf.add_page()
        serif = _load_serif(pdf)
        width = PAGE_W - 2 * MARGIN
        body_start_y = BODY_START_Y_COMPACT if compact else BODY_START_Y

        # --- letterhead (sits below the address zone on a PostGrid send;
        # near the top on a PCM send, which handles addressing separately) ---
        pdf.set_xy(MARGIN, body_start_y)
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(width, 6, _sanitize(advisor_name or "Your Advisor"), ln=1)
        if firm_name:
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(90, 90, 90)
            pdf.cell(width, 5, _sanitize(firm_name), ln=1)
            pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(width, 5, (date or datetime.now()).strftime("%B %d, %Y"), ln=1)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(4)

        # --- salutation + body ---
        pdf.set_font(serif, "", 11)
        pdf.cell(width, 6, _sanitize(f"Dear {first_name or 'Neighbor'},"), ln=1)
        pdf.ln(2)
        for para in _sanitize(body or DEFAULT_INVITE_BODY).split("\n\n"):
            pdf.multi_cell(width, 5.4, para.strip())
            pdf.set_x(MARGIN)
            pdf.ln(1.5)

        # --- the personal link + QR, side by side ---
        y = pdf.get_y() + 2
        qr_size = 28
        qr_img = qrcode.make(personal_url)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            qr_img.save(tmp.name)
            qr_path = tmp.name
        try:
            pdf.image(qr_path, x=MARGIN, y=y, w=qr_size)
        finally:
            try:
                os.remove(qr_path)
            except OSError:
                pass
        pdf.set_xy(MARGIN + qr_size + 6, y + 3)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(width - qr_size - 6, 5, "Your personal link (or scan the code):", ln=1)
        pdf.set_x(MARGIN + qr_size + 6)
        pdf.set_font("Helvetica", "", 12)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(width - qr_size - 6, 7, _sanitize(personal_url), ln=1)
        pdf.set_text_color(0, 0, 0)
        pdf.set_x(MARGIN + qr_size + 6)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(110, 110, 110)
        pdf.cell(width - qr_size - 6, 5, "This link is yours alone. It takes about two minutes.", ln=1)
        pdf.set_text_color(0, 0, 0)
        pdf.set_y(max(pdf.get_y(), y + qr_size) + 6)

        # --- sign-off ---
        pdf.set_font(serif, "", 11)
        pdf.cell(width, 6, "With warm regards,", ln=1)
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(width, 6, _sanitize(advisor_name or "Your Advisor"), ln=1)
        if firm_name:
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(width, 5, _sanitize(firm_name), ln=1)

        # --- footer: disclosure + production credit ---
        pdf.set_y(-24)
        pdf.set_x(MARGIN)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(120, 120, 120)
        if disclosure:
            pdf.multi_cell(width, 3.6, _sanitize(disclosure), align="C")
            pdf.set_x(MARGIN)
        pdf.multi_cell(width, 3.6,
                       "Letters are produced and mailed by VerbaPost Inc., Nashville, TN, on behalf of the advisor named above. "
                       "To be removed from future mailings, write to the return address on this envelope.",
                       align="C")

        if include_sample and SAMPLE_STORY.strip():
            _append_sample_story(pdf)

        raw = pdf.output(dest="S")
        if isinstance(raw, str):
            return raw.encode("latin-1")
        return bytes(raw)
    except Exception as e:
        logger.error(f"Invitation PDF failed: {e}")
        return None


def _append_sample_story(pdf):
    """Bind the finished sample letter in behind the invitation.

    Drawn with letter_format.render_story_header so this page is the same
    artifact a storyteller actually receives, not a mock-up of one. Auto page
    break is turned on for this section: a long story runs to a second sheet
    rather than overflowing off the page.
    """
    import letter_format

    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(letter_format.MARGIN_MM, letter_format.MARGIN_MM, letter_format.MARGIN_MM)
    pdf.set_y(letter_format.MARGIN_MM)

    # A small label so nobody mistakes the sample for their own letter.
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(130, 130, 130)
    pdf.set_x(letter_format.MARGIN_MM)
    pdf.multi_cell(0, 4, _sanitize(SAMPLE_NOTE), align="C")
    pdf.ln(6)
    pdf.set_text_color(0, 0, 0)

    letter_format.render_story_header(
        pdf, SAMPLE_STORYTELLER,
        question_text=SAMPLE_PROMPT or None,
        margin=letter_format.MARGIN_MM,
        page_width=letter_format.PAGE_WIDTH_MM)

    mono = "TypeRight" if "TypeRight" in getattr(pdf, "font_aliases", {}) else "Courier"
    pdf.set_font(mono, "", 11)
    pdf.set_x(letter_format.MARGIN_MM)
    pdf.multi_cell(0, 6, _sanitize(SAMPLE_STORY.strip()))

    # Leave the document as we found it for anything rendered afterwards.
    pdf.set_auto_page_break(auto=False)
    pdf.set_margins(MARGIN, MARGIN, MARGIN)
