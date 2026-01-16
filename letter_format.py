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
# "Manuscript" Margins (Wide for elegance)
MARGIN_INCHES = 1.5 
MARGIN_MM = 38.1 
PAGE_WIDTH_MM = 215.9  # US Letter
PAGE_HEIGHT_MM = 279.4 # US Letter

class LetterPDF(FPDF):
    """
    Custom PDF class for the Family Legacy Archive.
    Enforces the 'Manuscript' aesthetic (Vintage Font, Wide Margins).
    """
    def __init__(self, footer_text="Preserved by VerbaPost"):
        super().__init__(orientation='P', unit='mm', format='Letter')
        self.custom_footer_text = footer_text
        self.set_margins(MARGIN_MM, MARGIN_MM, MARGIN_MM)
        self.set_auto_page_break(auto=True, margin=MARGIN_MM)
        
    def header(self):
        # We handle the visual header manually in create_pdf so it only appears on Page 1
        pass

    def footer(self):
        """
        Archival Footer: Page numbers and Advisor Branding.
        """
        self.set_y(-20)
        
        # 1. Advisor Branding (Centered)
        # Check if the TypeRight font is active, otherwise Courier
        if 'TypeRight' in self.font_aliases:
            self.set_font('TypeRight', '', 8)
        else:
            self.set_font('Courier', '', 8)
            
        self.set_text_color(100, 100, 100) # Archive Grey
        self.cell(0, 5, self.custom_footer_text, align='C', ln=1)
        
        # 2. Page Numbers
        self.cell(0, 5, f'- Page {self.page_no()} -', align='C')

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

def create_pdf(body_text, to_addr, from_addr, advisor_firm="VerbaPost Archives", audio_url=None, is_marketing=False):
    """
    Generates the Single Standard 'Manuscript' PDF.
    Now supports is_marketing=True to remove the Family Archive header.
    """
    try:
        # 1. Initialize PDF (Manuscript Mode)
        footer_txt = f"Preserved by {advisor_firm}" if not is_marketing else "VerbaPost"
        pdf = LetterPDF(footer_text=footer_txt)
        
        # 2. Load Vintage Font (Corrected Path)
        font_family = 'Courier' # Fallback
        font_path = os.path.join("assets", "fonts", "type_right.ttf")
        
        # Try Assets Path First
        if os.path.exists(font_path):
            try:
                pdf.add_font('TypeRight', '', font_path, uni=True)
                font_family = 'TypeRight'
            except Exception as e:
                logger.error(f"Font Load Error (Assets): {e}")
        # Try Root Path Fallback
        elif os.path.exists("type_right.ttf"):
            try:
                pdf.add_font('TypeRight', '', 'type_right.ttf', uni=True)
                font_family = 'TypeRight'
            except Exception as e:
                logger.error(f"Font Load Error (Root): {e}")
        
        # 3. Add Page
        pdf.add_page()
        pdf.set_text_color(0, 0, 0)
        
        if is_marketing:
            # --- MARKETING HEADER (Clean) ---
            pdf.set_font(font_family, '', 12)
            
            # Sender Block
            sender_name = _safe_get(from_addr, 'name') or "VerbaPost"
            sender_addr = _safe_get(from_addr, 'address_line1')
            
            pdf.cell(0, 5, sender_name, ln=1, align='L')
            if sender_addr:
                pdf.cell(0, 5, sender_addr, ln=1, align='L')
            
            pdf.ln(10) # Gap
            
        else:
            # --- HEIRLOOM HEADER (The "Family Archive" Brand) ---
            pdf.set_font(font_family, '', 16)
            pdf.cell(0, 8, "THE FAMILY LEGACY ARCHIVE", align='C', ln=1)
            
            # Divider Line
            pdf.set_draw_color(50, 50, 50)
            y_line = pdf.get_y() + 2
            pdf.line(x1=MARGIN_MM, y1=y_line, x2=PAGE_WIDTH_MM - MARGIN_MM, y2=y_line)
            pdf.ln(5)
            
            # --- THE DEDICATION BLOCK ---
            storyteller = _safe_get(from_addr, 'name') or "The Family"
            rec_date = datetime.now().strftime("%B %d, %Y")
            
            pdf.set_font(font_family, '', 10)
            pdf.cell(0, 5, f"Storyteller: {storyteller}", align='C', ln=1)
            pdf.cell(0, 5, f"Recorded: {rec_date}", align='C', ln=1)
            pdf.cell(0, 5, f"Preserved by: {advisor_firm}", align='C', ln=1)
            
            pdf.ln(15) # Space before body starts

        # --- THE BODY ---
        pdf.set_font(font_family, '', 11)
        safe_body = _sanitize_text(body_text)
        pdf.multi_cell(0, 6, safe_body)
        
        # --- AUDIO QR CODE (The Digital Bridge) ---
        if audio_url and not is_marketing:
            _add_audio_qr(pdf, audio_url, PAGE_WIDTH_MM, PAGE_HEIGHT_MM, MARGIN_MM)

        # Output
        raw_output = pdf.output(dest='S')
        if isinstance(raw_output, str): return raw_output.encode('latin-1')
        elif isinstance(raw_output, bytearray): return bytes(raw_output)
        return raw_output
        
    except Exception as e:
        logger.error(f"PDF Generation Failed: {e}")
        return _create_error_pdf(str(e))

def _add_audio_qr(pdf, audio_url, w, h, margin):
    try:
        player_link = f"https://app.verbapost.com/?play={audio_url}"
        qr_img = qrcode.make(player_link)
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_qr:
            qr_img.save(tmp_qr.name)
            
            # Check for space
            y_pos = pdf.get_y() + 15
            if y_pos > (h - margin - 40): 
                pdf.add_page()
                y_pos = margin + 10
            
            x_center = (w - 30) / 2
            pdf.image(tmp_qr.name, x=x_center, y=y_pos, w=30)
            
            pdf.set_y(y_pos + 32)
            pdf.set_font("Helvetica", size=8) # Small clean font for instructions
            pdf.cell(0, 5, "Scan to listen to the original recording", align='C', ln=1)
            
        os.unlink(tmp_qr.name)
    except Exception: pass

def _create_error_pdf(msg):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Courier", size=12)
    pdf.cell(0, 10, f"Error: {msg}", ln=1)
    return pdf.output(dest='S').encode('latin-1')