from fpdf import FPDF
import os

def create_pdf(body_text, recipient_info, sender_info, is_heirloom=False, signature_path=None):
    """
    Generates a US Letter PDF with 1-inch margins.
    Embeds signature if provided.
    """
    # 1. Setup PDF (US Letter, Inches)
    pdf = FPDF(orientation='P', unit='in', format='Letter')
    
    # 2. Set Margins (1 inch = 25.4mm) - Fixes the "Half Letter" cut off
    pdf.set_margins(1.0, 1.0, 1.0)
    pdf.set_auto_page_break(auto=True, margin=1.0)
    
    pdf.add_page()
    
    # 3. Header (Sender Info)
    pdf.set_font("Arial", size=10)
    pdf.set_text_color(100, 100, 100) # Grey
    pdf.multi_cell(0, 0.2, sender_info.upper()) # Uppercase looks more formal
    pdf.ln(0.5)
    
    # 4. Date
    from datetime import datetime
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 0.2, datetime.now().strftime("%B %d, %Y"), ln=True)
    pdf.ln(0.5)
    
    # 5. Recipient Address (Bold)
    pdf.set_font("Arial", "B", 12)
    pdf.multi_cell(0, 0.25, recipient_info.upper())
    pdf.ln(0.75)
    
    # 6. Body Content
    if is_heirloom:
        pdf.set_font("Times", "I", 14) # Italic Serif
    else:
        pdf.set_font("Times", size=12) # Standard Serif
        
    pdf.multi_cell(0, 0.25, body_text)
    pdf.ln(0.5)
    
    # 7. Signature (The Fix)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 0.2, "Sincerely,", ln=True)
    pdf.ln(0.3)
    
    if signature_path and os.path.exists(signature_path):
        # Insert signature image (Width = 2 inches)
        # We use pdf.get_y() to place it exactly where the cursor is
        pdf.image(signature_path, x=1.0, w=2.0) 
        pdf.ln(0.5)
    else:
        # Fallback if no signature drawn
        pdf.ln(0.5)
        pdf.set_font("Script" if is_heirloom else "Arial", "I", 14)
        pdf.cell(0, 0.2, "Signed via VerbaPost", ln=True)

    # 8. Footer (Tiny)
    pdf.set_y(-0.5) # Move to bottom
    pdf.set_font("Arial", size=8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 0.2, "Sent via VerbaPost", align='C')
    
    return pdf.output(dest='S').encode('latin-1')