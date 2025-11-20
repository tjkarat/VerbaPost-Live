from fpdf import FPDF
import os

def create_pdf(text_content, recipient_info, return_address_info, is_heirloom, language="English", filename="output_letter.pdf", signature_path=None):
    print(f"📄 Formatting PDF in {language}...")
    
    pdf = FPDF(orientation='P', unit='mm', format='Letter')
    pdf.add_page()
    
    # --- FONT SELECTION ---
    font_map = {
        "English": "IndieFlower-Regular.ttf",
        "Chinese": "MaShanZheng-Regular.ttf",
        "Japanese": "Yomogi-Regular.ttf"
    }
    target_font = font_map.get(language, "IndieFlower-Regular.ttf")
    
    if os.path.exists(target_font):
        pdf.add_font('Handwriting', '', target_font)
        font_family = 'Handwriting'
    else:
        font_family = "Helvetica"

    # --- ADDRESS LOGIC ---
    if is_heirloom:
        # HEIRLOOM: Print addresses
        pdf.set_font("Helvetica", size=10)
        pdf.set_xy(10, 10)
        if return_address_info:
            pdf.multi_cell(0, 5, return_address_info)
        
        pdf.set_y(45)
        pdf.set_font("Helvetica", size=12)
        pdf.multi_cell(0, 6, recipient_info)
        pdf.set_y(80)
        
    else:
        # STANDARD (LOB): Leave top blank
        pdf.set_y(110)

    # --- BODY TEXT ---
    body_size = 16 if language in ["Chinese", "Japanese"] else 14
    pdf.set_font(font_family, size=body_size)
    pdf.multi_cell(0, 8, text_content)
    
    # --- SIGNATURE (THE FIX) ---
    pdf.ln(10)
    # We check if signature_path IS NOT NONE and EXISTS
    if signature_path and os.path.exists(signature_path):
        try:
            if pdf.get_y() > 250: pdf.add_page()
            pdf.image(signature_path, w=40) 
        except:
            pass
    
    # --- FOOTER ---
    if not is_heirloom:
        pdf.set_y(-20)
        pdf.set_font("Helvetica", 'I', 9)
        pdf.cell(0, 10, "Dictated via verbapost.com", ln=1, align='C')
    
    pdf.output(filename)
    return os.path.abspath(filename)