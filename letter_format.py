from fpdf import FPDF
import os

# 1. Font Configuration
# Maps "Legacy" archetypes to physical files.
# Ensure these .ttf files are in your root directory.
FONT_ARCHETYPES = {
    "The Executive": {"file": "Times-Bold.ttf", "family": "Times"},   # Strong, Serious
    "The Poet":      {"file": "Caveat-Regular.ttf", "family": "Caveat"}, # Emotional, Flowing
    "The Teacher":   {"file": "Schoolbell.ttf", "family": "Courier"}, # Neat, Educational
    "The Architect": {"file": "Roboto-Mono.ttf", "family": "Arial"},   # Clean, Modern
    "The Grandparent": {"file": "HomemadeApple.ttf", "family": "Caveat"} # Shaky, Authentic
}

class PDF(FPDF):
    def header(self):
        # Only add header if strictly necessary (e.g. page numbers for long letters)
        if self.page_no() > 1:
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'R')

    def footer(self):
        # Branding (Discreet)
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(150)
        self.cell(0, 10, 'VerbaPost Service', 0, 0, 'C')

def create_pdf(text, address_data, tier="Standard", font_style=None):
    """
    Generates a PDF binary.
    - Tier: Determines layout rules.
    - Font_Style: Used only for Legacy tier archetypes.
    """
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # --- FONT SELECTION LOGIC ---
    # Default: Standard Helvetica
    primary_font = "Helvetica"
    font_file = None

    # Logic: If Legacy, look up the Archetype. If Standard/Heirloom, use Caveat if available.
    if tier == "Legacy" and font_style:
        style_data = FONT_ARCHETYPES.get(font_style, FONT_ARCHETYPES["The Poet"])
        primary_font = style_data['family']
        font_file = style_data['file']
    elif tier in ["Heirloom", "Standard", "Campaign"]:
        # The 'Handwritten' feel for standard tiers
        primary_font = "Caveat"
        font_file = "Caveat-Regular.ttf"

    # Register Font (Safety Wrapper)
    try:
        if font_file and os.path.exists(font_file):
            pdf.add_font(primary_font, '', font_file, uni=True)
            pdf.set_font(primary_font, '', 12)
        else:
            # Fallback if file missing
            print(f"⚠️ Font file {font_file} missing. Falling back to Helvetica.")
            pdf.set_font("Helvetica", '', 12)
    except Exception as e:
        print(f"⚠️ Font Error: {e}")
        pdf.set_font("Helvetica", '', 12)

    # --- ADDRESS BLOCK (PostGrid Window Compliant) ---
    # Top Left: Sender (Return Address)
    pdf.set_font_size(10)
    pdf.set_text_color(50) # Dark Grey
    
    sender = [
        address_data.get('sender_name', ''),
        address_data.get('sender_street', ''),
        f"{address_data.get('sender_city', '')}, {address_data.get('sender_state', '')} {address_data.get('sender_zip', '')}"
    ]
    
    for line in sender:
        if line: pdf.cell(0, 5, line, ln=True)

    # Vertical Spacer for Envelope Window
    pdf.ln(25) 

    # Left Indent: Recipient (Target Address)
    # PostGrid requires this to be roughly at x=100mm, y=40-50mm
    pdf.set_x(100) 
    
    recipient = [
        address_data.get('recipient_name', ''),
        address_data.get('recipient_street', ''),
        address_data.get('recipient_city_state_zip', '') # Sometimes passed as one string
    ]
    
    # Handle split city/state if passed separately
    if not recipient[2]:
        recipient[2] = f"{address_data.get('recipient_city', '')}, {address_data.get('recipient_state', '')} {address_data.get('recipient_zip', '')}"

    for line in recipient:
        pdf.set_x(100) # Reset X for every line
        if line: pdf.cell(0, 6, line, ln=True)

    # --- LETTER BODY ---
    pdf.ln(35) # Space after address block
    
    # Restore Main Font Size
    pdf.set_font_size(12)
    pdf.set_text_color(0) # Black
    
    # Safe Rendering (UTF-8)
    try:
        pdf.multi_cell(0, 7, text)
    except Exception:
        # Emergency fallback for encoding crashes
        pdf.set_font("Helvetica", '', 12)
        cleaned_text = text.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 7, cleaned_text)

    # Return the binary buffer
    return pdf.output(dest='S').encode('latin-1')