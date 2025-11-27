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
    
    # Register Fonts
    font_map = {}
    if os.path.exists("Caveat-Regular.ttf"):
        pdf.add_font('Caveat', '', 'Caveat-Regular.ttf', uni=True)
        font_map['hand'] = 'Caveat'
    else: font_map['hand'] = 'Helvetica'

    if os.path.exists(CJK_PATH):
        try:
            pdf.add_font('NotoCJK', '', CJK_PATH, uni=True)
            font_map['cjk'] = 'NotoCJK'
        except: pass

    # --- HELPER: Draw Border ---
    def draw_santa_border():
        # Cream Background
        pdf.set_fill_color(252, 247, 235) 
        pdf.rect(0, 0, 215.9, 279.4, 'F')
        # Red/Green Border
        pdf.set_line_width(2)
        pdf.set_draw_color(180, 20, 20); pdf.rect(5, 5, 205.9, 269.4)
        pdf.set_line_width(1)
        pdf.set_draw_color(20, 100, 20); pdf.rect(8, 8, 199.9, 263.4)
        # Reset to black text
        pdf.set_text_color(0, 0, 0)

    # --- HELPER: Draw Header ---
    def draw_santa_header():
        pdf.set_y(20)
        pdf.set_font("Helvetica", "B", 24)
        pdf.set_text_color(180, 20, 20) 
        pdf.cell(0, 10, "FROM THE DESK OF SANTA CLAUS", 0, 1, 'C')
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(20, 100, 20) 
        pdf.cell(0, 5, "Official North Pole Correspondence | List Status: NICE", 0, 1, 'C')
        pdf.set_text_color(0, 0, 0)

    # 1. Create First Page
    pdf.add_page()
    
    if is_santa:
        draw_santa_border()
        draw_santa_header()

    # 2. Fonts
    if language in ["Japanese", "Chinese", "Korean"] and 'cjk' in font_map:
        body_font = font_map['cjk']; addr_font = font_map['cjk']; body_size = 12
    else:
        body_font = font_map['hand'] if (is_heirloom or is_santa) else 'Helvetica'
        addr_font = 'Helvetica' 
        body_size = 18 if is_santa else (16 if body_font == 'Caveat' else 12)

    # 3. Header Info
    pdf.set_text_color(0, 0, 0)
    
    # Date & Santa Address (Top Right)
    date_y = 50 if is_santa else 15
    pdf.set_xy(140, date_y)
    pdf.set_font(addr_font, '', 10)
    pdf.cell(60, 5, datetime.now().strftime("%B %d, %Y"), align='R', ln=1)
    
    if is_santa:
        pdf.set_x(140) # Align with date
        pdf.multi_cell(60, 5, "Santa Claus\n123 Elf Road\nNorth Pole, 88888", align='R')
    elif not is_santa:
        # Standard Return Address (Top Left)
        pdf.set_xy(15, 15)
        pdf.multi_cell(0, 5, return_addr)

    # Recipient
    recip_y = 80 if is_santa else 45
    pdf.set_xy(20, recip_y)
    pdf.set_font(addr_font, 'B', 12)
    pdf.multi_cell(0, 6, recipient_addr)

    # 4. Body Content
    pdf.set_xy(20, recip_y + 30)
    pdf.set_font(body_font, '', body_size)
    
    # Capture page number before writing text
    start_page = pdf.page_no()
    pdf.multi_cell(170, 8, content)
    end_page = pdf.page_no()

    # 5. Post-Processing for Multi-Page Santa Border
    # If text spilled to new pages, go back and draw borders/backgrounds on them
    if is_santa and end_page > start_page:
        for p in range(start_page + 1, end_page + 1):
            pdf.page = p
            # We have to redraw background/border without overwriting text
            # FPDF doesn't support layers easily, so we rely on the fact that
            # we set the fill color for the next page add.
            # A simple workaround for existing pages is tricky in standard FPDF.
            # We will rely on the white paper for subsequent pages or simple borders.
            # Drawing rects now would cover the text.
            pass 

    # 6. Signature
    pdf.ln(20)
    if is_santa:
        pdf.set_x(pdf.l_margin)
        pdf.set_font(font_map['hand'], '', 32)
        pdf.set_text_color(180, 20, 20)
        pdf.cell(0, 10, "Love, Santa", align='C', ln=1)
    elif signature_path and os.path.exists(signature_path):
        try: pdf.image(signature_path, x=20, w=40)
        except: pass
    
    # Footer
    pdf.set_y(-20)
    pdf.set_font('Helvetica', 'I', 8)
    pdf.set_text_color(100, 100, 100)
    footer = 'Official North Pole Mail' if is_santa else 'Dictated & Mailed via VerbaPost.com'
    pdf.cell(0, 10, footer, 0, 0, 'C')

    return pdf.output(dest="S")