import textwrap
from fpdf import FPDF
import io
import os
import logging
import tempfile
import qrcode
from datetime import datetime

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
# "Manuscript" Margins (Standardized)
MARGIN_MM = 38.1  # 1.5 inch Side Margins
PAGE_WIDTH_MM = 215.9 
PAGE_HEIGHT_MM = 279.4

class LetterPDF(FPDF):
    """
    Custom PDF class for the Family Legacy Archive.
    """
    def __init__(self, footer_text="Preserved by VerbaPost"):
        super().__init__(orientation='P', unit='mm', format='Letter')
        self.custom_footer_text = footer_text
        self.set_margins(MARGIN_MM, MARGIN_MM, MARGIN_MM)
        
        # Reduced bottom margin trigger to 20mm to fit more text
        self.set_auto_page_break(auto=True, margin=20) 
        
    def header(self):
        pass

    def footer(self):
        # Disable footer entirely if text is empty (Marketing Mode)
        if not self.custom_footer_text:
            return

        self.set_y(-20)
        
        # Serif, small, grey — a colophon line rather than a banner. The
        # advisor's credit sits here so the top of the page can belong to
        # the family.
        self.set_font('Times', 'I', 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 4, self.custom_footer_text, align='C', ln=1)
        self.set_font('Times', '', 7.5)
        self.cell(0, 4, str(self.page_no()), align='C')

def _sanitize_text(text):
    if not text: return ""
    text = str(text)
    replacements = {
        '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"',
        '\u2013': '-', '\u2014': '--', '\u2026': '...'
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text.encode('latin-1', 'replace').decode('latin-1')

def _safe_get(obj, key, default=""):
    if not obj: return default
    if isinstance(obj, dict): return obj.get(key, default)
    return getattr(obj, key, default)

def create_pdf(body_text, to_addr, from_addr, advisor_firm="VerbaPost Archives", audio_url=None, is_marketing=False, question_text=None, compliments_of=None, recipient_name=None):
    """
    Generates the Single Standard 'Manuscript' PDF.
    Now supports 'question_text' to appear in the dedication block.
    compliments_of (prospect acquisition path): replaces the "Preserved by"
    line with "With the compliments of: <advisor, firm>" and, with
    recipient_name, adds a "For: <name>" line — the letter is a gift.
    """
    try:
        # Disable footer for Marketing
        if is_marketing:
            footer_txt = ""
        elif compliments_of:
            footer_txt = f"With the compliments of {_sanitize_text(compliments_of)}"
        else:
            footer_txt = f"Preserved by {advisor_firm}"
        pdf = LetterPDF(footer_text=footer_txt)
        
        # 2. Load Vintage Font
        font_family = 'Courier' 
        font_path = os.path.join("assets", "fonts", "type_right.ttf")
        
        if os.path.exists(font_path):
            try:
                pdf.add_font('TypeRight', '', font_path, uni=True)
                font_family = 'TypeRight'
            except Exception as e:
                logger.error(f"Font Load Error: {e}")
        elif os.path.exists("type_right.ttf"):
            try:
                pdf.add_font('TypeRight', '', 'type_right.ttf', uni=True)
                font_family = 'TypeRight'
            except: pass
        
        pdf.add_page()
        pdf.set_text_color(0, 0, 0)
        
        if is_marketing:
            # --- MARKETING HEADER (Unbranded) ---
            pdf.set_font(font_family, '', 12)
            
            sender_name = _safe_get(from_addr, 'name')
            sender_addr = _safe_get(from_addr, 'address_line1')
            sender_city = _safe_get(from_addr, 'city') 
            
            if sender_name: pdf.cell(0, 5, sender_name, ln=1, align='L')
            if sender_addr: pdf.cell(0, 5, sender_addr, ln=1, align='L')
            
            # If city/state was parsed into 'city' field
            if sender_city and sender_city != sender_addr: 
                 pdf.cell(0, 5, sender_city, ln=1, align='L')

            pdf.ln(10) 
            
        else:
            render_story_header(pdf, _safe_get(from_addr, 'name'),
                                recipient_name=recipient_name,
                                question_text=question_text)

        # --- THE BODY ---
        pdf.set_font(font_family, '', 11)
        safe_body = _sanitize_text(body_text)
        pdf.multi_cell(0, 6, safe_body)
        
        # --- AUDIO QR CODE ---
        if audio_url and not is_marketing:
            _add_audio_qr(pdf, audio_url, PAGE_WIDTH_MM, PAGE_HEIGHT_MM, MARGIN_MM)

        raw_output = pdf.output(dest='S')
        if isinstance(raw_output, str): return raw_output.encode('latin-1')
        elif isinstance(raw_output, bytearray): return bytes(raw_output)
        return raw_output
        
    except Exception as e:
        logger.error(f"PDF Generation Failed: {e}")
        return _create_error_pdf(str(e))

def _add_audio_qr(pdf, audio_url, w, h, margin, recipient_id=None):
    """
    Generates a QR code with UTM tracking tags.
    """
    try:
        # 1. Clean the ID for URL safety
        safe_id = str(audio_url).strip()
        
        # 2. Add Tracking Tags (UTM Parameters)
        # This tells Google Analytics: "Source = Physical Letter", "Campaign = [The Recipient's ID]"
        tracker = f"?utm_source=physical_mail&utm_medium=qr_code&utm_campaign=letter_{safe_id}"
        
        # 3. Build Final Link
        # IMPORTANT: The tracker goes BEFORE the anchor or query params handled by the app logic
        # Ideally: https://app.verbapost.com/?play=123&utm_source=physical_mail...
        player_link = f"https://app.verbapost.com/{tracker}&play={safe_id}"
        
        # --- QR GENERATION ---
        qr_img = qrcode.make(player_link)
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_qr:
            qr_img.save(tmp_qr.name)
            y_pos = pdf.get_y() + 15
            
            # Page Break Logic
            if y_pos > (h - margin - 40): 
                pdf.add_page()
                y_pos = margin + 10
            
            x_center = (w - 30) / 2
            pdf.image(tmp_qr.name, x=x_center, y=y_pos, w=30)
            
            # Caption
            pdf.set_y(y_pos + 32)
            pdf.set_font("Helvetica", size=8) 
            pdf.cell(0, 5, "Scan to listen to the original recording", align='C', ln=1)
            
        os.unlink(tmp_qr.name)
    except Exception as e:
        logger.error(f"QR Error: {e}")

def _create_error_pdf(msg):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Courier", size=12)
    pdf.cell(0, 10, f"Error: {msg}", ln=1)
    return pdf.output(dest='S').encode('latin-1')


def render_story_header(pdf, storyteller, recipient_name=None, question_text=None,
                        recorded_on=None, margin=MARGIN_MM, page_width=PAGE_WIDTH_MM):
    """Draw the letter's header onto an existing FPDF page.

    Shared with invitation_format so the sample story printed inside a
    prospecting mailer is rendered by the same code as the letter a real
    storyteller receives — if this design changes, the sample changes with it
    instead of quietly drifting into a lie about the product.
    """
    name = _sanitize(storyteller) or "A Family Story"
    when = recorded_on or datetime.now()
    rec_date = f"{when:%B} {when.day}, {when.year}"

    pdf.set_font('Times', '', 22)
    pdf.set_text_color(20, 20, 20)
    pdf.set_x(margin)
    pdf.cell(0, 11, name, align='C', ln=1)

    pdf.set_font('Times', 'I', 10)
    pdf.set_text_color(115, 115, 115)
    pdf.set_x(margin)
    pdf.cell(0, 5, f"Recorded {rec_date}", align='C', ln=1)

    pdf.ln(4)
    y_line = pdf.get_y()
    inset = margin + 32
    pdf.set_draw_color(175, 175, 175)
    pdf.set_line_width(0.2)
    pdf.line(x1=inset, y1=y_line, x2=page_width - inset, y2=y_line)
    pdf.ln(8)

    if recipient_name:
        pdf.set_font('Times', 'I', 12)
        pdf.set_text_color(45, 45, 45)
        pdf.set_x(margin)
        pdf.cell(0, 6, f"For {_sanitize(recipient_name)}", align='C', ln=1)
        pdf.ln(4)

    if question_text:
        pdf.set_font('Times', 'I', 11)
        pdf.set_text_color(100, 100, 100)
        pdf.set_x(margin)
        pdf.multi_cell(0, 5.5, f'"{_sanitize(question_text)}"', align='C')
        pdf.ln(3)

    pdf.set_text_color(0, 0, 0)
    pdf.ln(8)
