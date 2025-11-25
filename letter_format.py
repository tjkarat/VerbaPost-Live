from fpdf import FPDF
import os
from datetime import datetime

class LetterPDF(FPDF):
    def header(self): pass 
    def footer(self):
        self.set_y(-0.6)
        self.set_font("Times", "I", 8)
        self.set_text_color(128)
        self.cell(0, 0.2, "Sent via VerbaPost", 0, 0, 'C')

def create_pdf(body_text, recipient_info, sender_info, is_heirloom=False, signature_path=None):
    # 1. Setup (US Letter)
    pdf = LetterPDF(orientation='P', unit='in', format='Letter')
    pdf.add_page()
    pdf.set_margins(1.0, 1.0, 1.0) 
    
    # Check for Handwriting Font
    caveat_path = "Caveat-Regular.ttf"
    has_handwriting = os.path.exists(caveat_path)
    if has_handwriting:
        pdf.add_font('Caveat', '', caveat_path, uni=True)

    # 2. HEADER (Sender Info) - Times New Roman
    pdf.set_xy(1.0, 1.0)
    pdf.set_font("Times", size=10)
    pdf.set_text_color(100, 100, 100) # Grey
    pdf.multi_cell(3.0, 0.2, sender_info.upper())
    
    # 3. DATE - Times New Roman
    # Fixed Y position ensures it doesn't overlap or repeat
    pdf.set_xy(1.0, 2.0)
    pdf.set_text_color(0, 0, 0) # Black
    pdf.cell(0, 0.2, datetime.now().strftime("%B %d, %Y"))
    
    # 4. RECIPIENT - Times New Roman (Bold)
    # Fixed Y position (Standard window envelope position)
    pdf.set_xy(1.0, 2.5)
    pdf.set_font("Times", "B", 12)
    pdf.multi_cell(4.0, 0.25, recipient_info.upper())
    
    # 5. BODY - Caveat (Handwriting)
    pdf.set_xy(1.0, 3.75) # Start body lower to clear address
    
    if has_handwriting:
        pdf.set_font("Caveat", size=20)
    elif is_heirloom:
        pdf.set_font("Times", "I", 14)
    else:
        pdf.set_font("Times", size=12)
        
    pdf.multi_cell(0, 0.3, body_text)
    
    # 6. SIGNATURE
    # We calculate Y based on where the body text ended
    current_y = pdf.get_y()
    pdf.set_xy(1.0, current_y + 0.3)
    
    # REMOVED "Sincerely," as requested
    
    if signature_path and os.path.exists(signature_path):
        # Place signature image
        pdf.image(signature_path, x=1.0, y=pdf.get_y(), w=2.0)
    else:
        # Fallback if no signature drawn
        pdf.ln(0.5)
        pdf.cell(0, 0.2, "Signed via VerbaPost")

    return pdf.output(dest='S').encode('latin-1')