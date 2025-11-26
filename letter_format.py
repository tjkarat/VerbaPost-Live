from fpdf import FPDF
import os
import requests
from datetime import datetime

# --- CONFIG ---
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
    ensure_fonts()
    
    pdf = FPDF(format='Letter')
    pdf.set_auto_page_break(True, margin=20)
    
    # Fonts
    font_map = {}
    if os.path.exists("Caveat-Regular.ttf"):
        pdf.add_font('Caveat', '', 'Caveat-Regular.ttf', uni=True)
        font_map['hand'] = 'Caveat'
    else: font_map['hand'] = 'Helvetica'

    if os.path.exists(CJK_PATH):
        try: pdf.add_font('NotoCJK', '', CJK_PATH, uni=True); font_map['cjk'] = 'NotoCJK'
        except: pass

    pdf.add_page()
    
    # Santa BG
    if is_santa and os.path.exists("santa_bg.jpg"):
        pdf.image("santa_bg.jpg", x=0, y=0, w=215.9, h=279.4)

    # Select Font
    if language in ["Japanese", "Chinese", "Korean"] and 'cjk' in font_map:
        body_font = font_map['cjk']; addr_font = font_map['cjk']; body_size = 12
    else:
        body_font = font_map['hand'] if (is_heirloom or is_santa) else 'Helvetica'
        addr_font = 'Helvetica' 
        body_size = 18 if is_santa else (16 if body_font == 'Caveat' else 12)

    # Content
    if not is_santa:
        pdf.set_font(addr_font, '', 10)
        pdf.set_xy(15, 15)
        pdf.multi_cell(0, 5, return_addr)
    
    # Date
    date_y = 55 if is_santa else 15 # Lower for Santa
    pdf.set_xy(150, date_y)
    pdf.set_font(addr_font, '', 10)
    pdf.cell(50, 0, datetime.now().strftime("%B %d, %Y"), align='R')
    
    # Recipient
    recip_y = 65 if is_santa else 45
    pdf.set_xy(20, recip_y)
    pdf.set_font(addr_font, 'B', 12)
    pdf.multi_cell(0, 6, recipient_addr)
    
    # Body
    body_y = 100 if is_santa else 80
    pdf.set_xy(20, body_y)
    pdf.set_font(body_font, '', body_size)
    pdf.multi_cell(170, 8, content)
    
    # Signature
    pdf.ln(20) # Space before sig
    
    if is_santa:
        # SANTA SIGNATURE FIX: Large, Right Aligned
        pdf.set_x(100) # Move to right half
        pdf.set_font(font_map['hand'], '', 28) # Bigger font
        pdf.cell(0, 10, "Love, Santa", align='R') 
    elif signature_path and os.path.exists(signature_path):
        try: pdf.image(signature_path, x=20, w=40)
        except: pass
    
    # Footer
    pdf.set_y(-20)
    pdf.set_font('Helvetica', 'I', 8)
    footer = 'North Pole Official Mail' if is_santa else 'Dictated & Mailed via VerbaPost.com'
    pdf.cell(0, 10, footer, 0, 0, 'C')

    return pdf.output(dest="S")