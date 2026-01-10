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
MARGIN_INCHES = 1.0
MARGIN_MM = 25.4
PAGE_WIDTH_MM = 215.9  # US Letter
PAGE_HEIGHT_MM = 279.4 # US Letter

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
        """
        Custom header logic.
        """
        pass

    def footer(self):
        """
        Standard Footer: Always sticks to the bottom.
        Includes Branding and Page Numbers (if multi-page).
        """
        # Position at 2.0 cm from bottom
        self.set_y(-20)
        
        # 1. Branding Text (Centered)
        self.set_font("Helvetica", size=8)
        self.set_text_color(150, 150, 150) # Light Grey
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
        '\u2013': '-', '\u2014': '--', '\u2026': '...'
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text.encode('latin-1', 'replace').decode('latin-1')

def _safe_get(obj, key, default=""):
    """Helper to get value from either a dict or an object attribute."""
    if not obj: return default
    if isinstance(obj, dict): return obj.get(key, default)
    return getattr(obj, key, default)

def create_pdf(body_text, to_addr, from_addr, tier="Standard", signature_text="", audio_url=None):
    """
    Generates the final PDF bytes for the letter.
    Supports Audio QR Code if audio_url is provided.
    """
    try:
        # 1. Determine Footer Text
        footer_msg = "Sent via VerbaPost.com"
        if tier == "Vintage" or tier == "Heirloom":
            footer_msg = "Dictated and Mailed by VerbaPost.com"
        elif tier == "Civic":
            footer_msg = "Civic Action Letter via VerbaPost.com"

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

        # 5. Header Content (Date, From, To)
        pdf.set_font(font_family, size=12)
        pdf.set_text_color(0, 0, 0)
        
        # Date
        current_date = datetime.now().strftime("%B %d, %Y")
        pdf.cell(0, 5, current_date, ln=1)
        pdf.ln(5)
        
        # From Address Block
        f_name = _safe_get(from_addr, 'name') or _safe_get(from_addr, 'company')
        f_street = _safe_get(from_addr, 'address_line1') or _safe_get(from_addr, 'street')
        f_line2 = _safe_get(from_addr, 'address_line2') or _safe_get(from_addr, 'street2')
        f_city = _safe_get(from_addr, 'city')
        f_state = _safe_get(from_addr, 'state')
        f_zip = _safe_get(from_addr, 'zip_code') or _safe_get(from_addr, 'zip')
        
        from_lines = [f_name, f_street, f_line2, f"{f_city}, {f_state} {f_zip}"]
        from_text = "\n".join([str(L) for L in from_lines if L and str(L).strip() != ",  "])
        pdf.multi_cell(0, 5, _sanitize_text(from_text))
        pdf.ln(5)

        # To Address Block
        t_name = _safe_get(to_addr, 'name')
        t_street = _safe_get(to_addr, 'address_line1') or _safe_get(to_addr, 'street')
        t_line2 = _safe_get(to_addr, 'address_line2') or _safe_get(to_addr, 'street2')
        t_city = _safe_get(to_addr, 'city')
        t_state = _safe_get(to_addr, 'state')
        t_zip = _safe_get(to_addr, 'zip_code') or _safe_get(to_addr, 'zip')

        to_lines = [t_name, t_street, t_line2, f"{t_city}, {t_state} {t_zip}"]
        to_text = "\n".join([str(L) for L in to_lines if L and str(L).strip() != ",  "])
        pdf.multi_cell(0, 5, _sanitize_text(to_text))
        
        # Space before body
        pdf.ln(10)

        # 6. Render Letter Body
        # Removed hardcoded set_y to allow natural flow after address blocks
        
        safe_body = _sanitize_text(body_text)
        if not safe_body.strip(): safe_body = "[No Content Provided]"
            
        pdf.multi_cell(0, 6, safe_body)
        
        # 7. Signature
        if signature_text:
             pdf.ln(10)
             pdf.set_font(font_family, 'I', 14) 
             pdf.cell(0, 10, _sanitize_text(signature_text), ln=1)

        # 8. AUDIO QR CODE (Heirloom)
        if audio_url:
            try:
                # Construct Player URL
                # Note: Ideally fetch base_url from env/secrets, using hardcoded fallback per prompt
                player_link = f"https://app.verbapost.com/?play={audio_url}"
                
                # Generate QR
                qr_img = qrcode.make(player_link)
                
                # Use temp file to insert into FPDF
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_qr:
                    qr_img.save(tmp_qr.name)
                    
                    # Position: Bottom Center of Current Page
                    # A4 Width ~210mm / US Letter ~215mm
                    # QR Width 30mm
                    # X = (215.9 - 30) / 2 = ~92.95
                    
                    # Calculate vertical position: Ensure it fits or add page
                    y_pos = pdf.get_y() + 10
                    if y_pos > (PAGE_HEIGHT_MM - MARGIN_MM - 40): # Check if space remains
                        pdf.add_page()
                        y_pos = MARGIN_MM + 10
                    
                    x_center = (PAGE_WIDTH_MM - 30) / 2
                    pdf.image(tmp_qr.name, x=x_center, y=y_pos, w=30)
                    
                    # Add Caption
                    pdf.set_y(y_pos + 32)
                    pdf.set_font("Helvetica", size=9)
                    pdf.cell(0, 5, "Scan to listen to this story", align='C', ln=1)
                    
                os.unlink(tmp_qr.name) # Cleanup
                
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