from fpdf import FPDF
import os

def create_pdf(body_text, recipient_info, sender_info, is_heirloom=False):
    """
    Generates a PDF for printing/mailing.
    Forces US Letter size (8.5 x 11) for PostGrid compliance.
    """
    # FIX: Explicitly set format to 'Letter' (default is A4)
    pdf = FPDF(orientation='P', unit='in', format='Letter')
    pdf.add_page()
    
    # 1. Font Setup
    pdf.set_font("Arial", size=12)
    
    # 2. Header (Sender Info) - Top Left
    pdf.set_text_color(100, 100, 100) # Grey
    pdf.multi_cell(0, 0.2, sender_info)
    pdf.ln(0.5) # Line break in inches
    
    # 3. Date
    from datetime import datetime
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 0.2, datetime.now().strftime("%B %d, %Y"), ln=True)
    pdf.ln(0.5)
    
    # 4. Recipient Address
    pdf.set_font("Arial", "B", 12)
    pdf.multi_cell(0, 0.25, recipient_info)
    pdf.ln(1.0)
    
    # 5. Body Content
    if is_heirloom:
        pdf.set_font("Times", "I", 14) # Italic for Heirloom
    else:
        pdf.set_font("Times", size=12)
        
    pdf.multi_cell(0, 0.3, body_text)
    
    # 6. Footer
    pdf.ln(1.0)
    pdf.set_font("Arial", "I", 10)
    pdf.cell(0, 0.2, "Sent via VerbaPost", ln=True, align='C')
    
    return pdf.output(dest='S').encode('latin-1')