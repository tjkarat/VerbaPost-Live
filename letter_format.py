from fpdf import FPDF
import os
from datetime import datetime

class LetterPDF(FPDF):
    def header(self):
        pass 
    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-0.6)
        self.set_font("Arial", "I", 8)
        self.set_text_color(128)
        self.cell(0, 0.2, "Sent via VerbaPost", 0, 0, 'C')

def create_pdf(body_text, recipient_info, sender_info, is_heirloom=False, signature_path=None):
    """
    Generates a US Letter PDF with 1-inch margins.
    Uses 'Caveat' for body text if available to simulate handwriting.
    """
    # 1. Setup (US Letter)
    pdf = LetterPDF(orientation='P', unit='in', format='Letter')
    pdf.add_page()
    pdf.set_margins(1.0, 1.0, 1.0) 
    
    # --- FONT LOADING ---
    # We check if the file exists to prevent crashing
    caveat_path = "Caveat-Regular.ttf"
    has_handwriting = os.path.exists(caveat_path)
    
    if has_handwriting:
        # Register the font (must be .ttf)
        pdf.add_font('Caveat', '', caveat_path, uni=True)

    # --- SENDER INFO (Top Left) ---
    pdf.set_xy(1.0, 1.0)
    pdf.set_font("Arial", size=10)
    pdf.set_text_color(100, 100, 100) # Grey
    pdf.multi_cell(3.0, 0.2, sender_info.upper())
    
    # --- DATE ---
    pdf.set_xy(1.0, 2.0)
    pdf.set_text_color(0, 0, 0) # Black
    pdf.cell(0, 0.2, datetime.now().strftime("%B %d, %Y"))
    
    # --- RECIPIENT INFO ---
    pdf.set_xy(1.0, 2.75)
    pdf.set_font("Arial", "B", 12)
    pdf.multi_cell(4.0, 0.25, recipient_info.upper())
    
    # --- BODY TEXT (THE UPDATE) ---
    pdf.set_xy(1.0, 4.0)
    
    if has_handwriting:
        # Caveat looks small, so we bump size to 16 or 18 for readability
        pdf.set_font("Caveat", size=18)
    elif is_heirloom:
        pdf.set_font("Times", "I", 14)
    else:
        pdf.set_font("Times", size=12)
        
    pdf.multi_cell(0, 0.3, body_text)
    
    # --- SIGNATURE ---
    current_y = pdf.get_y()
    pdf.set_xy(1.0, current_y + 0.5)
    
    if has_handwriting:
        pdf.set_font("Caveat", size=18)
    else:
        pdf.set_font("Times", "", 12)
        
    pdf.cell(0, 0.2, "Sincerely,", ln=True)
    
    if signature_path and os.path.exists(signature_path):
        # Signature Image
        pdf.image(signature_path, x=1.0, y=pdf.get_y() + 0.2, w=2.0)
    else:
        # Fallback Text Signature
        pdf.ln(0.5)
        if has_handwriting:
            pdf.set_font("Caveat", size=24)
        else:
            pdf.set_font("Script" if is_heirloom else "Arial", "I", 14)
        pdf.cell(0, 0.2, "Signed via VerbaPost")

    return pdf.output(dest='S').encode('latin-1')