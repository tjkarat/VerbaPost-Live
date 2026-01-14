import textwrap
from fpdf import FPDF
import io
import os
import logging
import tempfile
import qrcode
from datetime import datetime, timedelta, timezone

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
MARGIN_INCHES = 1.0
MARGIN_MM = 25.4
PAGE_WIDTH_MM = 215.9  # US Letter
PAGE_HEIGHT_MM = 279.4 # US Letter

def get_cst_time():
    """Returns current time in CST (UTC-6) formatted for display."""
    # Fixed offset for CST (Standard Time)
    offset = timezone(timedelta(hours=-6))
    return datetime.now(offset).strftime("%B %d, %Y")

class LetterPDF(FPDF):
    """
    Custom PDF class to handle headers, footers, and page logic
    for VerbaPost letters.
    """
    def __init__(self, tier="Standard", footer_text="Sent via VerbaPost.com"):
        super().__init__(orientation='P', unit='mm', format='Letter')
        self.tier = tier
        self.custom_footer_text = footer_text
        self.set_margins(MARGIN_MM, MARGIN_MM, MARGIN_MM)
        self.set_auto_page_break(auto=True, margin=MARGIN_MM)
        
    def header(self):
        # Header logic is handled manually in create_pdf to allow
        # dynamic placement on the first page versus subsequent pages.
        pass

    def footer(self):
        """
        Standard Footer: Always sticks to the bottom.
        """
        # Position at 2.0 cm from bottom
        self.set_y(-20)
        
        # 1. Branding Text (Centered)
        self.set_font("Helvetica", size=8)
        self.set_text_color(120, 120, 120) # Grey
        self.cell(0, 5, self.custom_footer_text, align='C', ln=1)
        
        # 2. Page Numbers (if more than 1 page)
        if self.page_no() > 1:
            if self.tier == "Vintage":
                self.set_font('Courier', 'I', 8)
            else:
                self.set_font('Times', 'I', 8)
            self.cell(0, 5, f'Page {self.page_no()}', align='C')

def _sanitize_text(text):
    """
    Cleans text to ensure it is compatible with FPDF's latin-1 encoding.
    """
    if not text: return ""
    text = str(text)
    replacements = {
        '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"',
        '\u2013': '-', '\u2014': '--', '\u2026': '...',
        '\u2010': '-', '\u2011': '-'
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text.encode('latin-1', 'replace').decode('latin-1')

def _safe_get(obj, key, default=""):
    """Helper to get value from either a dict or an object attribute."""
    if not obj: return default
    if isinstance(obj, dict): return obj.get(key, default)
    return getattr(obj, key, default)

def create_pdf(body_text, to_addr, from_addr, tier="Standard", signature_text="", audio_url=None, metadata=None):
    """
    Generates the final PDF bytes for the letter.
    """
    if metadata is None: metadata = {}
    
    try:
        # 1. Determine Footer Text
        # Check for Firm Name first (B2B SaaS Branding)
        firm_name = metadata.get('firm_name')
        
        if firm_name:
            footer_msg = f"Compliments of {firm_name}"
        elif tier == "Vintage" or tier == "Heirloom":
            footer_msg = "Preserved by VerbaPost.com"
        elif tier == "Civic":
            footer_msg = "Civic Action Letter via VerbaPost.com"
        else:
            footer_msg = "Sent via VerbaPost.com"

        # 2. Initialize PDF
        pdf = LetterPDF(tier=tier, footer_text=footer_msg)
        
        # 3. Configure Fonts
        font_family = 'Times'
        if tier == "Vintage":
            if os.path.exists("type_right.ttf"):
                try:
                    pdf.add_font('TypeRight', '', 'type_right.ttf')
                    font_family = 'TypeRight'
                except Exception: font_family = 'Courier'
            else:
                font_family = 'Courier'

        # 4. Add Page
        pdf.add_page()

        # ---------------------------------------------------------
        # 5. HEADER CONTENT (Logic Branching)
        # ---------------------------------------------------------
        pdf.set_text_color(0, 0, 0)
        
        if tier == "Heirloom":
            # --- LAYOUT A: THE FAMILY STORY (Metadata Driven) ---
            
            # Top Right: Date
            pdf.set_font("Helvetica", size=10)
            export_date_str = f"Exported: {get_cst_time()}"
            start_y = pdf.get_y()
            pdf.cell(0, 5, export_date_str, align='R', ln=1)
            
            # Top Left: Storyteller Metadata
            pdf.set_y(start_y) # Reset Y to same line as date
            
            storyteller = _sanitize_text(metadata.get('storyteller', 'Unknown Storyteller'))
            interview_date = _sanitize_text(metadata.get('interview_date', ''))
            question = _sanitize_text(metadata.get('question_text', ''))

            pdf.set_font(font_family, 'B', 11)
            pdf.cell(0, 5, f"Storyteller: {storyteller}", ln=1)
            
            if interview_date:
                pdf.set_font(font_family, '', 11)
                pdf.cell(0, 5, f"Recorded:    {interview_date}", ln=1)
                
            if question:
                pdf.ln(2)
                pdf.set_font(font_family, 'B', 11)
                pdf.cell(15, 5, "Topic: ", ln=0)
                pdf.set_font(font_family, 'I', 11)
                remaining_w = PAGE_WIDTH_MM - (MARGIN_MM * 2) - 15
                pdf.multi_cell(remaining_w, 5, question)
            
            # Separator
            pdf.ln(5)
            line_y = pdf.get_y()
            pdf.line(MARGIN_MM, line_y, PAGE_WIDTH_MM - MARGIN_MM, line_y)
            pdf.ln(10)

        else:
            # --- LAYOUT B: STANDARD / VINTAGE / MARKETING (Address Driven) ---
            # Used for Admin Marketing Studio & Store Letters
            
            # 1. Date (Right Aligned)
            pdf.set_font(font_family, size=11)
            pdf.cell(0, 5, get_cst_time(), align='R', ln=1)
            
            # 2. From Address (Top Left)
            pdf.set_y(MARGIN_MM) # Reset to top margin
            
            from_name = _sanitize_text(_safe_get(from_addr, 'name'))
            from_street = _sanitize_text(_safe_get(from_addr, 'address_line1') or _safe_get(from_addr, 'street'))
            # Admin console packs everything into 'address_line1' often, which is fine
            
            if from_name or from_street:
                pdf.set_font(font_family, size=10)
                pdf.multi_cell(100, 5, f"{from_name}\n{from_street}")
            
            # 3. Spacing for Recipient
            pdf.ln(15)
            
            # 4. To Address
            to_name = _sanitize_text(_safe_get(to_addr, 'name'))
            to_street = _sanitize_text(_safe_get(to_addr, 'street') or _safe_get(to_addr, 'address_line1'))
            to_city = _sanitize_text(_safe_get(to_addr, 'city'))
            to_state = _sanitize_text(_safe_get(to_addr, 'state'))
            to_zip = _sanitize_text(_safe_get(to_addr, 'zip'))
            
            # Combine city/state/zip if present, or rely on street if it contains them (Admin Console)
            to_block = f"{to_name}\n{to_street}"
            if to_city and to_state:
                to_block += f"\n{to_city}, {to_state} {to_zip}"
                
            pdf.set_font(font_family, size=12)
            pdf.multi_cell(0, 6, to_block)
            
            # 5. Divider Line (Optional styling for Vintage)
            pdf.ln(10)
            if tier == "Vintage":
                 y = pdf.get_y()
                 pdf.set_draw_color(150, 150, 150)
                 pdf.line(MARGIN_MM, y, PAGE_WIDTH_MM - MARGIN_MM, y)
                 pdf.set_draw_color(0, 0, 0) # Reset
                 pdf.ln(10)
            else:
                 pdf.ln(5)

        # ---------------------------------------------------------
        # 6. BODY CONTENT
        # ---------------------------------------------------------
        pdf.set_font(font_family, size=12)
        safe_body = _sanitize_text(body_text)
        if not safe_body.strip(): safe_body = "[No Content Provided]"
            
        pdf.multi_cell(0, 6, safe_body)
        
        # 7. Signature
        if signature_text:
             pdf.ln(10)
             pdf.set_font(font_family, 'I', 14) 
             pdf.cell(0, 10, _sanitize_text(signature_text), ln=1)

        # 8. AUDIO QR CODE (Heirloom Only)
        # We generally only show QR codes for Heirloom tier, but if audio_url exists we print it.
        if audio_url:
            try:
                # Check vertical space. If near bottom, add page.
                if pdf.get_y() > (PAGE_HEIGHT_MM - MARGIN_MM - 50):
                    pdf.add_page()
                else:
                    pdf.ln(15)

                player_link = f"https://app.verbapost.com/?play={audio_url}"
                qr_img = qrcode.make(player_link)
                
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_qr:
                    qr_img.save(tmp_qr.name)
                    
                    # Center the QR Code
                    x_center = (PAGE_WIDTH_MM - 30) / 2
                    y_pos = pdf.get_y()
                    
                    pdf.image(tmp_qr.name, x=x_center, y=y_pos, w=30)
                    
                    # Caption
                    pdf.set_y(y_pos + 32)
                    pdf.set_font("Helvetica", size=9)
                    pdf.set_text_color(100, 100, 100) # Grey caption
                    pdf.cell(0, 5, "Scan to listen to this story", align='C', ln=1)
                    
                os.unlink(tmp_qr.name)
            except Exception as e:
                logger.error(f"QR Generation Error: {e}")

        # 9. Output
        raw_output = pdf.output(dest='S')
        if isinstance(raw_output, str): return raw_output.encode('latin-1')
        elif isinstance(raw_output, bytearray): return bytes(raw_output)
        return raw_output
        
    except Exception as e:
        logger.error(f"PDF Generation Failed: {e}")
        return _create_error_pdf(str(e))

def _create_error_pdf(error_message):
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        pdf.set_text_color(255, 0, 0)
        pdf.cell(0, 10, "Error Generating Letter PDF", ln=1)
        pdf.set_font("Courier", size=10)
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(0, 5, f"Details:\n{error_message}")
        raw = pdf.output(dest='S')
        if isinstance(raw, str): return raw.encode('latin-1')
        return bytes(raw)
    except: return b""