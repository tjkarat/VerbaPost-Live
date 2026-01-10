import textwrap
from fpdf import FPDF
import io
import os
import logging
import tempfile

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
        Currently empty as we don't want a header on every page for personal letters.
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
    Replaces common smart quotes and em-dashes with standard ASCII.
    """
    if not text:
        return ""
    
    text = str(text)
    
    replacements = {
        '\u2018': "'",  # Left single quote
        '\u2019': "'",  # Right single quote
        '\u201c': '"',  # Left double quote
        '\u201d': '"',  # Right double quote
        '\u2013': '-',  # En dash
        '\u2014': '--', # Em dash
        '\u2026': '...',# Ellipsis
    }
    
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
        
    # Final fallback: encode to latin-1 and ignore/replace unmappable chars
    return text.encode('latin-1', 'replace').decode('latin-1')

def _safe_get(obj, key, default=""):
    """
    Helper to get value from either a dict or an object attribute.
    Fixes the 'StandardAddress object has no attribute get' error.
    """
    if not obj: return default
    
    # If it's a dictionary
    if isinstance(obj, dict):
        return obj.get(key, default)
        
    # If it's an object (like StandardAddress)
    return getattr(obj, key, default)

def _format_address_block(addr_obj):
    """
    Formats an address object (Dict or StandardAddress) into a standard multi-line string.
    """
    if not addr_obj:
        return ""
        
    lines = []
    
    # Name
    name = _safe_get(addr_obj, 'name', '').strip()
    if name:
        lines.append(name)
        
    # Street Address (Line 1)
    street1 = _safe_get(addr_obj, 'address_line1', '').strip() or _safe_get(addr_obj, 'street', '').strip()
    if street1:
        lines.append(street1)
        
    # Street Address (Line 2 - Optional)
    street2 = _safe_get(addr_obj, 'address_line2', '').strip()
    if street2:
        lines.append(street2)
        
    # City, State Zip
    city = _safe_get(addr_obj, 'city', '').strip()
    state = _safe_get(addr_obj, 'state', '').strip()
    zip_code = _safe_get(addr_obj, 'zip_code', '').strip() or _safe_get(addr_obj, 'zip', '').strip()
    
    city_line = f"{city}, {state} {zip_code}".strip()
    if city_line != ",":
        lines.append(city_line)
        
    return "\n".join(lines)

def create_pdf(body_text, to_addr, from_addr, tier="Standard", signature_text="", audio_url=None):
    """
    Generates the final PDF bytes for the letter.
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
        
        # 3. Configure Fonts & Styling based on Tier
        font_family = 'Times'
        
        if tier == "Vintage":
            # Attempt to load custom font
            if os.path.exists("type_right.ttf"):
                try:
                    pdf.add_font('TypeRight', '', 'type_right.ttf')
                    font_family = 'TypeRight'
                except Exception as e:
                    logger.warning(f"Could not load custom font: {e}")
                    font_family = 'Courier'
            else:
                font_family = 'Courier'

        # 4. Add Page
        pdf.add_page()

        # --- FIX: ADDRESS BLOCKS REMOVED ---
        # The address printing block has been removed here to support pre-printed stationery/envelopes.
        
        # 5. Position Cursor for Body
        # --- FIX: Removed pdf.set_y(100) ---
        # We now start just below the top margin to utilize the full page.
        pdf.set_y(MARGIN_MM + 10)
        
        # 6. Render Letter Body
        pdf.set_font(font_family, size=12)
        pdf.set_text_color(0, 0, 0) # Black text
        
        safe_body = _sanitize_text(body_text)
        
        if not safe_body.strip():
            safe_body = "[No Content Provided]"
            
        # Write Body
        pdf.multi_cell(0, 6, safe_body)
        
        # 7. Signature
        if signature_text:
             pdf.ln(10)
             pdf.set_font(font_family, 'I', 14) 
             pdf.cell(0, 10, _sanitize_text(signature_text), ln=1)

        # 8. Output (Byte Safety)
        raw_output = pdf.output(dest='S')
        
        # Ensure we return clean bytes
        if isinstance(raw_output, str):
            return raw_output.encode('latin-1')
        elif isinstance(raw_output, bytearray):
            return bytes(raw_output)
        return raw_output
        
    except Exception as e:
        logger.error(f"PDF Generation Failed: {e}")
        return _create_error_pdf(str(e))

def _create_error_pdf(error_message):
    """
    Fallback function to generate a PDF containing the error message.
    """
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
        elif isinstance(raw, bytearray): return bytes(raw)
        return raw
    except:
        return b""