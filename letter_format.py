from fpdf import FPDF

def create_pdf(body_text, recipient_info, sender_info, is_heirloom=False, language="English"):
    """
    Generates a PDF for printing.
    """
    pdf = FPDF()
    pdf.add_page()
    
    # 1. Font Setup
    pdf.set_font("Arial", size=12)
    
    # 2. Header (Sender Info) - Top Left
    pdf.set_text_color(100, 100, 100) # Grey for sender
    pdf.multi_cell(0, 5, sender_info)
    pdf.ln(10)
    
    # 3. Date
    from datetime import datetime
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, datetime.now().strftime("%B %d, %Y"), ln=True)
    pdf.ln(10)
    
    # 4. Recipient Address (For Window Envelopes)
    pdf.set_font("Arial", "B", 12)
    pdf.multi_cell(0, 6, recipient_info)
    pdf.ln(20)
    
    # 5. Body Content
    pdf.set_font("Times", size=12)
    
    if is_heirloom:
        # simulated handwriting font or just italic for now
        pdf.set_font("Times", "I", 14)
        
    pdf.multi_cell(0, 8, body_text)
    
    # 6. Footer / Signature
    pdf.ln(20)
    pdf.set_font("Arial", "I", 10)
    pdf.cell(0, 10, "Sent via VerbaPost", ln=True, align='C')
    
    # Return PDF as bytes
    return pdf.output(dest='S').encode('latin-1')