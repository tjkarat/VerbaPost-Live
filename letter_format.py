from fpdf import FPDF
import os

def create_pdf(text_content, recipient_info, return_address_info, is_heirloom, language="English", filename="output_letter.pdf", signature_path="temp_signature.png"):
    print(f"📄 Formatting PDF in {language}...")
    
    # A4 is safer for Lob globally, but Letter is standard US. 
    # We use 'Letter' (215.9 mm x 279.4 mm)
    pdf = FPDF(orientation='P', unit='mm', format='Letter')
    pdf.add_page()
    
    # --- FONT SETUP ---
    font_family = "Helvetica"
    font_map = {
        "English": "IndieFlower-Regular.ttf",
        "Chinese": "MaShanZheng-Regular.ttf",
        "Japanese": "Yomogi-Regular.ttf"
    }
    target_font = font_map.get(language, "IndieFlower-Regular.ttf")
    
    if os.path.exists(target_font):
        pdf.add_font('Handwriting', '', target_font)
        font_family = 'Handwriting'

    # --- LAYOUT LOGIC ---
    if is_heirloom:
        # HEIRLOOM: Needs addresses printed so YOU can see them to hand-write the envelope
        # 1. Return Address (Top Left)
        pdf.set_font("Helvetica", size=10)
        pdf.set_xy(10, 10)
        if return_address_info:
            pdf.multi_cell(0, 5, return_address_info)
        
        # 2. Recipient Address (Window Position)
        pdf.set_y(45)
        pdf.set_font("Helvetica", size=12)
        pdf.multi_cell(0, 6, recipient_info)
        
        # 3. Start Body below address
        pdf.set_y(80)
        
    else:
        # STANDARD (LOB): 
        # Lob prints the address on a separate page 1.
        # We just want the letter content to start comfortably at the top of Page 2.
        # Standard margin is 10mm, let's give it 20mm to look nice.
        pdf.set_y(20)

    # --- BODY TEXT ---
    body_size = 16 if language in ["Chinese", "Japanese"] else 14
    pdf.set_font(font_family, size=body_size)
    pdf.multi_cell(0, 8, text_content)
    
    # --- SIGNATURE ---
    pdf.ln(10)
    if os.path.exists(signature_path):
        try:
            # Use current X, auto Y
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