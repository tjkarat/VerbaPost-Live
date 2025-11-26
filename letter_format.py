from fpdf import FPDF
import os
import requests
from datetime import datetime

# --- FONT CONFIGURATION ---
# Only download Caveat (Handwriting). We will use standard Helvetica for headers to avoid artifacts.
FONT_MAP = {
    "Caveat-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/caveat/Caveat-Regular.ttf",
}

# Fallback for Asian characters
CJK_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

def ensure_fonts():
    """Checks for fonts locally; downloads them if missing."""
    for filename, url in FONT_MAP.items():
        if not os.path.exists(filename):
            try:
                r = requests.get(url, allow_redirects=True)
                if r.status_code == 200:
                    with open(filename, "wb") as f: f.write(r.content)
            except: pass

def create_pdf(content, recipient_addr, return_addr, is_heirloom, language="English", signature_path=None):
    # 1. Ensure fonts exist
    ensure_fonts()
    
    # 2. Init PDF (Letter Size)
    pdf = FPDF(format='Letter')
    pdf.set_auto_page_break(True, margin=20)
    
    # 3. Register Fonts
    font_map = {}
    
    # Handwriting (Caveat) - For the Body
    if os.path.exists("Caveat-Regular.ttf"):
        pdf.add_font('Caveat', '', 'Caveat-Regular.ttf', uni=True)
        font_map['hand'] = 'Caveat'
    else:
        font_map['hand'] = 'Helvetica' # Fallback

    # CJK (Asian Characters)
    if os.path.exists(CJK_PATH):
        try:
            pdf.add_font('NotoCJK', '', CJK_PATH, uni=True)
            font_map['cjk'] = 'NotoCJK'
        except: pass

    pdf.add_page()
    
    # Select Body Font
    if language in ["Japanese", "Chinese", "Korean"] and 'cjk' in font_map:
        body_font = font_map['cjk']
        addr_font = font_map['cjk']
        body_size = 12
    else:
        body_font = font_map['hand'] 
        addr_font = 'Helvetica' # Use standard system font for headers (Cleanest look)
        body_size = 16 if body_font == 'Caveat' else 12

    # --- CONTENT ---
    
    # 1. Return Address (Top Left)
    # Using Helvetica to prevent "garbage" artifacts
    pdf.set_font(addr_font, '', 10)
    current_y = 15
    for line in return_addr.split('\n'):
        clean_line = line.strip()
        if clean_line:
            pdf.text(15, current_y, clean_line) # X=15 for safe margin
            current_y += 5
    
    # 2. Date (Top Right)
    pdf.set_xy(150, 15)
    pdf.cell(50, 0, datetime.now().strftime("%B %d, %Y"), align='R')
    
    # 3. Recipient (Window Envelope Position)
    pdf.set_font(addr_font, 'B', 12)
    current_y = 45 
    for line in recipient_addr.split('\n'):
        clean_line = line.strip()
        if clean_line:
            pdf.text(20, current_y, clean_line)
            current_y += 6
    
    # 4. Body Text
    pdf.set_xy(15, 80) 
    pdf.set_font(body_font, '', body_size)
    pdf.multi_cell(0, 8, content)
    
    # 5. Signature Image (Fixed Placement)
    if signature_path and os.path.exists(signature_path):
        # Calculate Y position below the body text
        sig_y = pdf.get_y() + 10
        
        # If signature would fall off the page (height > 250mm), add a new page
        if sig_y > 250:
            pdf.add_page()
            sig_y = 20
            
        try: 
            # Place image at X=15, Calculated Y, Width=40mm
            pdf.image(signature_path, x=15, y=sig_y, w=40)
        except Exception as e:
            print(f"Signature Error: {e}")
            pass
    
    # 6. Footer
    pdf.set_y(-20)
    pdf.set_font(addr_font, 'I', 8) # Italic Helvetica
    pdf.cell(0, 10, 'Dictated & Mailed via VerbaPost.com', 0, 0, 'C')

    # Return Raw Bytes
    return pdf.output(dest="S")