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
        
        if 'TypeRight' in self.font_aliases:
            self.set_font('TypeRight', '', 8)
        else:
            self.set_font('Courier', '', 8)
            
        self.set_text_color(100, 100, 100) 
        self.cell(0, 5, self.custom_footer_text, align='C', ln=1)
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

def create_pdf(body_text, to_addr, from_addr, advisor_firm="VerbaPost Archives", audio_url=None, is_marketing=False, question_text=None):
    """
    Generates the Single Standard 'Manuscript' PDF.
    Now supports 'question_text' to appear in the dedication block.
    """
    try:
        # Disable footer for Marketing
        footer_txt = f"Preserved by {advisor_firm}" if not is_marketing else ""
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
            # --- HEIRLOOM HEADER (Branded) ---
            pdf.set_font(font_family, '', 16)
            pdf.cell(0, 8, "THE FAMILY LEGACY ARCHIVE", align='C', ln=1)

            # TAGLINE
            pdf.set_font(font_family, '', 10)
            pdf.cell(0, 5, "A letter your grandchildren will hold.", align='C', ln=1)
            
            pdf.set_draw_color(50, 50, 50)
            y_line = pdf.get_y() + 2
            pdf.line(x1=MARGIN_MM, y1=y_line, x2=PAGE_WIDTH_MM - MARGIN_MM, y2=y_line)
            pdf.ln(6)
            
            storyteller = _safe_get(from_addr, 'name') or "The Family"
            rec_date = datetime.now().strftime("%B %d, %Y")
            
            # --- INFO BLOCK (CENTERED & STACKED) ---
            pdf.set_font(font_family, '', 10)
            
            # 1. Storyteller
            pdf.cell(0, 5, f"Storyteller: {storyteller}", align='C', ln=1)
            
            # 2. Question
            if question_text:
                pdf.set_font(font_family, '', 9)
                pdf.multi_cell(0, 5, f"Question: {question_text}", align='C')
                pdf.set_font(font_family, '', 10) # Reset font
            
            # 3. Date (FORCED CENTERING)
            pdf.ln(2) 
            pdf.set_x(MARGIN_MM) # <--- Force cursor back to left margin to prevent offset
            pdf.cell(0, 5, f"Recorded: {rec_date}", align='C', ln=1)
            
            # 4. Preserved By
            pdf.set_x(MARGIN_MM) # <--- Force cursor back to left margin
            pdf.cell(0, 5, f"Preserved by: {advisor_firm}", align='C', ln=1)
            
            pdf.ln(15) 

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

def _add_audio_qr(pdf, audio_url, w, h, margin):
    try:
        # CAMPAIGN TRACKING
        player_link = f"https://app.verbapost.com/?play={audio_url}&utm_source=letter&utm_medium=qr"
        
        qr_img = qrcode.make(player_link)
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_qr:
            qr_img.save(tmp_qr.name)
            y_pos = pdf.get_y() + 15
            if y_pos > (h - margin - 40): 
                pdf.add_page()
                y_pos = margin + 10
            
            x_center = (w - 30) / 2
            pdf.image(tmp_qr.name, x=x_center, y=y_pos, w=30)
            pdf.set_y(y_pos + 32)
            pdf.set_font("Helvetica", size=8) 
            pdf.cell(0, 5, "Scan to listen to the original recording", align='C', ln=1)
        os.unlink(tmp_qr.name)
    except Exception: pass

def _create_error_pdf(msg):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Courier", size=12)
    pdf.cell(0, 10, f"Error: {msg}", ln=1)
    return pdf.output(dest='S').encode('latin-1')