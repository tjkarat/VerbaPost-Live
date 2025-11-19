from fpdf import FPDF
import os

def create_pdf(text_content, recipient_info, return_address_info, is_heirloom, filename="output_letter.pdf", signature_path="temp_signature.png"):
    print("📄 Formatting PDF...")
    
    pdf = FPDF(orientation='P', unit='mm', format='Letter')
    pdf.add_page()
    
    font_path = 'IndieFlower-Regular.ttf'
    has_cursive = False
    if os.path.exists(font_path):
        pdf.add_font('IndieFlower', '', font_path)
        has_cursive = True

    # --- 1. RETURN ADDRESS (Top Left, Small) ---
    # Standard Arial, smaller size
    pdf.set_font("Helvetica", size=10)
    # We put this at the very top margin
    pdf.set_xy(10, 10)
    if return_address_info:
        pdf.multi_cell(0, 5, return_address_info)
    
    # --- 2. RECIPIENT ADDRESS ---
    # Move down to standard window position (approx 40-50mm from top)
    pdf.set_y(45)
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(0, 6, recipient_info)
    
    # --- 3. BODY TEXT ---
    pdf.ln(15) # Gap before body
    if has_cursive:
        pdf.set_font('IndieFlower', size=14)
    else:
        pdf.set_font("Helvetica", size=12)
    
    pdf.multi_cell(0, 8, text_content)
    
    # --- 4. SIGNATURE ---
    pdf.ln(10)
    if os.path.exists(signature_path):
        try:
            # w=40 keeps it reasonable
            pdf.image(signature_path, w=40) 
        except:
            print("Could not load signature image")
    
    # --- 5. FOOTER (Conditional) ---
    # Only print if NOT Heirloom
    if not is_heirloom:
        pdf.set_y(-20)
        pdf.set_font("Helvetica", 'I', 9)
        pdf.cell(0, 10, "Dictated via verbapost.com", ln=1, align='C')
    
    pdf.output(filename)
    return os.path.abspath(filename)