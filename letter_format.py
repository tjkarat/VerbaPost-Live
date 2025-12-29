import textwrap
from fpdf import FPDF
import io
import os
import logging

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
    def __init__(self, tier="Standard"):
        super().__init__(orientation='P', unit='mm', format='Letter')
        self.tier = tier
        self.set_margins(MARGIN_MM, MARGIN_MM, MARGIN_MM)
        self.set_auto_page_break(auto=True, margin=MARGIN_MM)
        
    def header(self):
        """
        Custom header logic. 
        For 'Vintage' letters, we might add a subtle date stamp or mark.
        For now, we keep it clean to maximize writing space.
        """
        pass

    def footer(self):
        """
        Adds page numbers if the letter exceeds one page.
        """
        if self.page_no() > 1:
            self.set_y(-15)
            # Select font for footer
            if self.tier == "Vintage":
                self.set_font('Courier', 'I', 8)
            else:
                self.set_font('Times', 'I', 8)
            
            self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def _sanitize_text(text):
    """
    Cleans text to ensure it is compatible with FPDF's latin-1 encoding.
    Replaces common smart quotes and em-dashes with standard ASCII.
    """
    if not text:
        return ""
    
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

def _format_address_block(addr_dict):
    """
    Formats a dictionary address into a standard multi-line string.
    """
    if not addr_dict:
        return ""
        
    lines = []
    
    # Name
    name = addr_dict.get('name', '').strip()
    if name:
        lines.append(name)
        
    # Street Address (Line 1)
    street1 = addr_dict.get('address_line1', '').strip() or addr_dict.get('street', '').strip()
    if street1:
        lines.append(street1)
        
    # Street Address (Line 2 - Optional)
    street2 = addr_dict.get('address_line2', '').strip()
    if street2:
        lines.append(street2)
        
    # City, State Zip
    city = addr_dict.get('city', '').strip()
    state = addr_dict.get('state', '').strip()
    zip_code = addr_dict.get('zip_code', '').strip() or addr_dict.get('zip', '').strip()
    
    city_line = f"{city}, {state} {zip_code}".strip()
    if city_line != ",":
        lines.append(city_line)
        
    return "\n".join(lines)

def create_pdf(body_text, to_addr, from_addr, tier="Standard", signature_text=""):
    """
    Generates the final PDF bytes for the letter.
    
    Args:
        body_text (str): The raw text content of the letter.
        to_addr (dict): Recipient address details.
        from_addr (dict): Sender address details.
        tier (str): 'Standard', 'Vintage', or 'Civic'.
        signature_text (str): Optional signature override.
        
    Returns:
        bytes: The raw PDF file content.
    """
    try:
        # 1. Initialize PDF
        pdf = LetterPDF(tier=tier)
        pdf.add_page()
        
        # 2. Configure Fonts & Styling based on Tier
        # Vintage = Courier (Typewriter style)
        # Standard/Civic = Times New Roman (Formal)
        
        font_family = 'Times'
        header_font_family = 'Helvetica'
        
        if tier == "Vintage":
            font_family = 'Courier'
            header_font_family = 'Courier'
        
        # 3. Render Sender Address (Top Right)
        # Standard business letter format places sender info at the top.
        pdf.set_font(header_font_family, size=10)
        pdf.set_text_color(80, 80, 80) # Dark Grey
        
        sender_block = _format_address_block(from_addr)
        sender_lines = sender_block.split('\n')
        
        # Calculate width needed for right alignment
        # We manually position the cursor for each line to align right
        for line in sender_lines:
            safe_line = _sanitize_text(line)
            w = pdf.get_string_width(safe_line) + 2
            pdf.set_x(PAGE_WIDTH_MM - MARGIN_MM - w)
            pdf.cell(w, 5, safe_line, ln=1, align='R')
            
        pdf.ln(10) # Spacer (approx 2 lines)
        
        # 4. Render Recipient Address (Top Left)
        pdf.set_font(header_font_family, size=10)
        pdf.set_text_color(0, 0, 0) # Black
        
        recipient_block = _format_address_block(to_addr)
        # Sanitize entire block
        safe_recipient_block = _sanitize_text(recipient_block)
        
        pdf.multi_cell(0, 5, safe_recipient_block, align='L')
        
        pdf.ln(15) # Spacer before body (approx 3 lines)
        
        # 5. Render Letter Body
        
        pdf.set_font(font_family, size=12)
        pdf.set_text_color(0, 0, 0) # Black text
        
        safe_body = _sanitize_text(body_text)
        
        # Check if body is empty
        if not safe_body.strip():
            safe_body = "[No Content Provided]"
            
        # Write the body text
        # Multi_cell handles word wrapping automatically within margins
        pdf.multi_cell(0, 6, safe_body)
        
        # Optional Signature handling if passed
        if signature_text:
             pdf.ln(10)
             # Basic signature simulation
             pdf.set_font(font_family, 'I', 14) 
             pdf.cell(0, 10, _sanitize_text(signature_text), ln=1)
        
        # 6. Add "Sent via VerbaPost" Footer (Subtle)
        
        current_y = pdf.get_y()
        space_left = PAGE_HEIGHT_MM - MARGIN_MM - current_y
        
        if space_left < 20:
            pdf.add_page()
            
        pdf.ln(15)
        pdf.set_font("Helvetica", size=8)
        pdf.set_text_color(150, 150, 150) # Light Grey
        
        footer_text = "Sent via VerbaPost.com"
        if tier == "Vintage":
            footer_text = "Typewritten & Mailed by VerbaPost.com"
        elif tier == "Civic":
            footer_text = "Civic Action Letter via VerbaPost.com"
            
        pdf.cell(0, 5, footer_text, align='C')
        
        # 7. Output
        # CRITICAL FIX: Handle FPDF2 bytearray vs string output safely
        raw_output = pdf.output(dest='S')
        if isinstance(raw_output, str):
            return raw_output.encode('latin-1')
        return bytes(raw_output)
        
    except Exception as e:
        logger.error(f"PDF Generation Failed: {e}")
        # Return a simple error PDF so the system doesn't crash completely
        return _create_error_pdf(str(e))

def _create_error_pdf(error_message):
    """
    Fallback function to generate a PDF containing the error message.
    Useful for debugging production systems without exposing logs to users.
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
        
        # CRITICAL FIX: Safety Cast for Error PDF too
        raw = pdf.output(dest='S')
        if isinstance(raw, str): return raw.encode('latin-1')
        return bytes(raw)
    except:
        return b""