from fpdf import FPDF
import os
from datetime import datetime

def create_pdf(content, recipient_addr, return_addr, is_heirloom, language, filename="letter.pdf", signature_path=None):
    pdf = FPDF()
    pdf.add_page()
    
    # --- FONT SELECTION ---
    # Default to Helvetica (Standard for English)
    font_family = 'Helvetica'
    
    # If CJK, we must load the external font we installed via packages.txt
    if language in ["Japanese", "Chinese", "Korean"]:
        # Path where Debian/Ubuntu installs Noto CJK
        font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
        
        if os.path.exists(font_path):
            try:
                # Add the font. 'uni=True' tells FPDF to use Unicode.
                pdf.add_font('NotoCJK', '', font_path, uni=True)
                font_family = 'NotoCJK'
            except Exception as e:
                print(f"Font Load Error: {e}")
        else:
            print("⚠️ CJK Font file not found on server.")

    # --- LAYOUT ---
    
    # 1. Return Address (Top Left)
    pdf.set_font(font_family, '', 10)
    pdf.set_xy(10, 10)
    pdf.multi_cell(0, 5, return_addr)
    
    # 2. Recipient Address (Shifted for Window Envelope)
    pdf.set_xy(20, 40) # Standard window position
    pdf.set_font(font_family, '', 12) # Bold often breaks on CJK if not specifically loaded, so stick to regular
    pdf.multi_cell(0, 6, recipient_addr)
    
    # 3. Date
    pdf.set_xy(160, 10)
    pdf.set_font(font_family, '', 10)
    pdf.cell(0, 10, datetime.now().strftime("%Y-%m-%d"), ln=True, align='R')
    
    # 4. Body Content
    pdf.set_xy(10, 80)
    pdf.set_font(font_family, '', 12)
    
    # FPDF multi_cell handles wrapping
    pdf.multi_cell(0, 6, content)
    
    # 5. Signature
    if signature_path and os.path.exists(signature_path):
        pdf.ln(10) # Space before sig
        # Add image. w=40 maintains aspect ratio, roughly 40mm wide
        pdf.image(signature_path, w=40)
    
    # 6. Footer / Branding
    pdf.set_y(-20)
    pdf.set_font(font_family, '', 8) # Use main font for footer too to be safe
    pdf.cell(0, 10, 'Dictated via VerbaPost.com', 0, 0, 'C')

    # Save
    save_path = f"/tmp/{filename}"
    pdf.output(save_path)
    return save_path
