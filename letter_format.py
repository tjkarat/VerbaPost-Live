from fpdf import FPDF
import os
import requests
from datetime import datetime

# --- FONT CONFIGURATION ---
FONT_MAP = {
    "Caveat-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/caveat/Caveat-Regular.ttf",
}
CJK_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

def ensure_fonts():
    for filename, url in FONT_MAP.items():
        if not os.path.exists(filename):
            try:
                r = requests.get(url, allow_redirects=True)
                if r.status_code == 200:
                    with open(filename, "wb") as f: f.write(r.content)
            except: pass

def create_pdf(content, recipient_addr, return_addr, is_heirloom, language="English", signature_path=None, is_santa=False):
    # 1. Ensure fonts
    ensure_fonts()
    
    # 2. Init PDF
    pdf = FPDF(format='Letter')
    pdf.set_auto_page_break(True, margin=20)
    
    # 3. Register Fonts
    font_map = {}
    
    # Handwriting (Caveat)
    if os.path.exists("Caveat-Regular.ttf"):
        pdf.add_font('Caveat', '', 'Caveat-Regular.ttf', uni=True)
        font_map['hand'] = 'Caveat'
    else: font_map['hand'] = 'Helvetica'

    # CJK
    if os.path.exists(CJK_PATH):
        try: pdf.add_font('NotoCJK', '', CJK_PATH, uni=True); font_map['cjk'] = 'NotoCJK'
        except: pass

    pdf.add_page()
    
    # --- SANTA BACKGROUND ---
    if is_santa and os.path.exists("santa_bg.jpg"):
        # Place image covering the whole page (215.9mm x 279.4mm is Letter size)
        pdf.image("santa_bg.jpg", x=0, y=0, w=215.9, h=279.4)

    # Select Fonts
    if language in ["Japanese", "Chinese", "Korean"] and 'cjk' in font_map:
        body_font = font_map['cjk']; addr_font = font_map['cjk']; body_size = 12
    else:
        # Santa letters always use handwriting for body
        body_font = font_map['hand'] if (is_heirloom or is_santa) else 'Helvetica'
        addr_font = 'Helvetica' 
        body_size = 16 if body_font == 'Caveat' else 12

    # --- CONTENT ---
    
    # 1. Return Address (Skip if Santa - it's in the header image, or hardcoded)
    if not is_santa:
        pdf.set_font(addr_font, '', 10)
        current_y = 15
        for line in return_addr.split('\n'):
            if line.strip(): pdf.text(15, current_y, line.strip()); current_y += 5
    
    # 2. Date
    # Move date down for Santa so it doesn't hit the header graphics
    date_y = 45 if is_santa else 15
    pdf.set_xy(150, date_y)
    pdf.set_font(addr_font, '', 10)
    pdf.cell(50, 0, datetime.now().strftime("%B %d, %Y"), align='R')
    
    # 3. Recipient (Window Envelope Position)
    # For Santa, we might want this slightly adjusted, but standard window is fixed pos.
    pdf.set_font(addr_font, 'B', 12)
    current_y = 50 if is_santa else 45
    for line in recipient_addr.split('\n'):
        if line.strip(): pdf.text(20, current_y, line.strip()); current_y += 6
    
    # 4. Body Text
    # Push text down for Santa to clear the header image
    body_start_y = 90 if is_santa else 80
    pdf.set_xy(20, body_start_y) # Indent slightly (X=20)
    pdf.set_font(body_font, '', body_size)
    # Reduce width slightly (170) so it doesn't hit the candy cane borders
    pdf.multi_cell(170, 8, content)
    
    # 5. Signature
    if signature_path and os.path.exists(signature_path):
        pdf.ln(10)
        try: pdf.image(signature_path, x=20, w=40) # Align left
        except: pass
    elif is_santa:
        # Text signature if no digital one provided
        pdf.ln(10)
        pdf.set_font(font_map['hand'], '', 20)
        pdf.cell(0, 10, "Love, Santa", ln=True)
    
    # 6. Footer
    pdf.set_y(-20)
    pdf.set_font('Helvetica', 'I', 8)
    footer_text = 'North Pole Official Mail' if is_santa else 'Dictated & Mailed via VerbaPost.com'
    pdf.cell(0, 10, footer_text, 0, 0, 'C')

    return pdf.output(dest="S")