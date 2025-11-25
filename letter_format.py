from fpdf import FPDF
import os
from datetime import datetime

class LetterPDF(FPDF):
    def header(self):
        pass 
    def footer(self):
        self.set_y(-0.6)
        self.set_font("Times", "I", 8)
        self.set_text_color(128)
        self.cell(0, 0.2, "Sent via VerbaPost", 0, 0, 'C')

def create_pdf(body_text, recipient_info, sender_info, is_heirloom=False, signature_path=None):
    # 1. Setup
    pdf = LetterPDF(orientation='P', unit='in', format='Letter')
    pdf.add_page()
    pdf.set_margins(1.0, 1.0, 1.0) 
    
    # Load Custom Font (Caveat)
    caveat_path = "Caveat-Regular.ttf"
    has_handwriting = os.path.exists(caveat_path)
    if has_handwriting:
        pdf.add_font('Caveat', '', caveat_path, uni=True)

    # 2. Header & Sender (Times New Roman)
    pdf.set_xy(1.0, 1.0)
    pdf.set_font("Times", size=10) # Changed from Arial
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(3.0, 0.2, sender_info.upper())
    
    # 3. Date (Times New Roman)
    pdf.set_xy(1.0, 2.0)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Times", size=10)
    pdf.cell(0, 0.2, datetime.now().strftime("%B %d, %Y"))
    
    # 4. Recipient (Times New Roman Bold)
    pdf.set_xy(1.0, 2.75)
    pdf.set_font("Times", "B", 12) # Changed from Arial
    pdf.multi_cell(4.0, 0.25, recipient_info.upper())
    
    # 5. Body (Caveat / Handwriting)
    pdf.set_xy(1.0, 4.0)
    
    if has_handwriting:
        pdf.set_font("Caveat", size=20) # Increased size for readability
    elif is_heirloom:
        pdf.set_font("Times", "I", 14)
    else:
        pdf.set_font("Times", size=12)
        
    pdf.multi_cell(0, 0.3, body_text)
    
    # 6. Closing (Match Body Font)
    current_y = pdf.get_y()
    pdf.set_xy(1.0, current_y + 0.5)
    
    if has_handwriting:
        pdf.set_font("Caveat", size=20)
    else:
        pdf.set_font("Times", "", 12)
        
    pdf.cell(0, 0.2, "Sincerely,", ln=True)
    
    # 7. Signature Image
    if signature_path and os.path.exists(signature_path):
        pdf.image(signature_path, x=1.0, y=pdf.get_y() + 0.1, w=2.0)
    else:
        pdf.ln(0.5)
        pdf.cell(0, 0.2, "Signed via VerbaPost")

    return pdf.output(dest='S').encode('latin-1')