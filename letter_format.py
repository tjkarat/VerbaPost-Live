from fpdf import FPDF
import os

def create_pdf(text_content, recipient_info, return_address_info, is_heirloom, language="English", filename="output_letter.pdf", signature_path="temp_signature.png"):
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

    # --- ADDRESS LOGIC (THE FIX) ---
    # If Heirloom: Print addresses so Tarak can see them.
    # If Standard (Lob): Leave top blank. Lob adds a cover page with addresses.
    
    if is_heirloom:
        # 1. RETURN ADDRESS
        pdf.set_font("Helvetica", size=10)
        pdf.set_xy(10, 10)
        if return_address_info:
            pdf.multi_cell(0, 5, return_address_info)
        
        # 2. RECIPIENT ADDRESS
        pdf.set_y(45)
        pdf.set_font("Helvetica", size=12)
        pdf.multi_cell(0, 6, recipient_info)
        
        # Start body after address
        pdf.set_y(80)
    else:
        # STANDARD TIER: Leave 2 inches (50mm) blank at top for letterhead feel
        # Lob adds a separate page 1, so our text starts on page 2 (or page 1 of content)
        # We just start the text at a nice margin.
        pdf.set_y(40)

    # --- 3. BODY TEXT ---
    body_size = 16 if language in ["Chinese", "Japanese"] else 14
    pdf.set_font(font_family, size=body_size)
    pdf.multi_cell(0, 8, text_content)
    
    # --- 4. SIGNATURE ---
    pdf.ln(10)
    if os.path.exists(signature_path):
        try:
            pdf.image(signature_path, w=40) 
        except:
            pass
    
    # --- 5. FOOTER ---
    if not is_heirloom:
        pdf.set_y(-20)
        pdf.set_font("Helvetica", 'I', 9)
        pdf.cell(0, 10, "Dictated via verbapost.com", ln=1, align='C')
    
    pdf.output(filename)
    return os.path.abspath(filename)