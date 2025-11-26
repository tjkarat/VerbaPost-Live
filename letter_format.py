from fpdf import FPDF
import os
import requests
from datetime import datetime

# --- FONT SOURCES ---
FONTS = {
    "Caveat": "https://github.com/google/fonts/raw/main/ofl/caveat/Caveat-Regular.ttf",
    "Roboto": "https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Regular.ttf",
    "Roboto-Bold": "https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Bold.ttf"
}
CJK_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

def ensure_fonts():
    """Downloads fonts to current directory."""
    for name, url in FONTS.items():
        filename = f"{name}.ttf"
        if not os.path.exists(filename):
            try:
                r = requests.get(url, allow_redirects=True)
                if r.status_code == 200:
                    with open(filename, "wb") as f: f.write(r.content)
            except: pass

def create_pdf(content, recipient_addr, return_addr, is_heirloom, language="English", signature_path=None):
    # 1. Ensure fonts
    ensure_fonts()
    
    # 2. Init PDF
    pdf = FPDF(format='Letter')
    pdf.set_auto_page_break(True, margin=20)
    
    # 3. Register Fonts
    font_map = {}
    
    # Handwriting
    if os.path.exists("Caveat.ttf"):
        pdf.add_font('Caveat', '', 'Caveat.ttf', uni=True)
        font_map['hand'] = 'Caveat'
    else: font_map['hand'] = 'Helvetica'

    # Standard
    if os.path.exists("Roboto.ttf") and os.path.exists("Roboto-Bold.ttf"):
        pdf.add_font('Roboto', '', 'Roboto.ttf', uni=True)
        pdf.add_font('Roboto', 'B', 'Roboto-Bold.ttf', uni=True)
        font_map['sans'] = 'Roboto'
    else: font_map['sans'] = 'Helvetica'

    # CJK
    if os.path.exists(CJK_PATH):
        try:
            pdf.add_font('NotoCJK', '', CJK_PATH, uni=True)
            font_map['cjk'] = 'NotoCJK'
        except: pass

    pdf.add_page()
    
    # Select Font
    if language in ["Japanese", "Chinese", "Korean"] and 'cjk' in font_map:
        body_font = font_map['cjk']
        addr_font = font_map['cjk']
        body_size = 12
    else:
        body_font = font_map['hand'] 
        addr_font = font_map['sans'] 
        body_size = 16 if body_font == 'Caveat' else 12

    # --- CONTENT (Using Absolute Positioning for Headers to fix glitches) ---
    
    # 1. Return Address (Top Left)
    pdf.set_font(addr_font, '', 10)
    current_y = 15 # Start Y position
    for line in return_addr.split('\n'):
        if line.strip():
            pdf.text(12, current_y, line.strip()) # Absolute text placement
            current_y += 5
    
    # 2. Date (Top Right)
    pdf.set_xy(150, 15)
    pdf.cell(50, 0, datetime.now().strftime("%Y-%m-%d"), align='R')
    
    # 3. Recipient (Window Envelope Position - Fixed)
    pdf.set_font(addr_font, 'B', 12)
    current_y = 45 # Window envelope sweet spot
    for line in recipient_addr.split('\n'):
        if line.strip():
            pdf.text(20, current_y, line.strip())
            current_y += 6
    
    # 4. Body (Use MultiCell for wrapping)
    pdf.set_xy(15, 80) # Start body lower
    pdf.set_font(body_font, '', body_size)
    pdf.multi_cell(0, 8, content)
    
    # 5. Signature
    if signature_path and os.path.exists(signature_path):
        pdf.ln(10)
        try: pdf.image(signature_path, w=40)
        except: pass
    
    # 6. Footer
    pdf.set_y(-20)
    pdf.set_font(addr_font, '', 8)
    pdf.cell(0, 10, 'Dictated via VerbaPost.com', 0, 0, 'C')

    # Return Raw Bytes
    return pdf.output(dest="S")