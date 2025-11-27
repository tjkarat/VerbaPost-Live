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
            except: pass# --- CUSTOM PDF CLASS ---
class LetterPDF(FPDF):
    def __init__(self, is_santa=False, **kwargs):
        super().__init__(**kwargs)
        self.is_santa = is_santa

    def header(self):
        # This runs automatically every time a new page is added
        if self.is_santa:
            # 1. Cream Background
            self.set_fill_color(252, 247, 235) 
            self.rect(0, 0, 215.9, 279.4, 'F')
            
            # 2. Festive Borders
            self.set_line_width(2)
            self.set_draw_color(180, 20, 20) # Red
            self.rect(5, 5, 205.9, 269.4)
            
            self.set_line_width(1)
            self.set_draw_color(20, 100, 20) # Green
            self.rect(8, 8, 199.9, 263.4)
            
            # 3. Header Text (Only on Page 1)
            if self.page_no() == 1:
                self.set_y(20)
                self.set_font("Helvetica", "B", 24)
                self.set_text_color(180, 20, 20) 
                self.cell(0, 10, "FROM THE DESK OF SANTA CLAUS", 0, 1, 'C')
                
                self.set_font("Helvetica", "I", 10)
                self.set_text_color(20, 100, 20) 
                self.cell(0, 5, "Official North Pole Correspondence | List Status: NICE", 0, 1, 'C')
                self.set_text_color(0, 0, 0) # Reset text colordef create_pdf(content, recipient_addr, return_addr, is_heirloom, language="English", signature_path=None, is_santa=False):
    ensure_fonts()
    
    # Initialize using the Custom Class
    pdf = LetterPDF(is_santa=is_santa, format='Letter')
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

    # Create First Page
    pdf.add_page()

    # Fonts
    if language in ["Japanese", "Chinese", "Korean"] and 'cjk' in font_map:
        body_font = font_map['cjk']; addr_font = font_map['cjk']; body_size = 12
    else:
        body_font = font_map['hand'] if (is_heirloom or is_santa) else 'Helvetica'
        addr_font = 'Helvetica' 
        body_size = 18 if is_santa else (16 if body_font == 'Caveat' else 12)

    # --- CONTENT PLACEMENT ---
    pdf.set_text_color(0, 0, 0)
    
    # 1. Date (Top Right)
    date_y = 50 if is_santa else 15
    pdf.set_xy(140, date_y)
    pdf.set_font(addr_font, '', 10)
    pdf.cell(60, 5, datetime.now().strftime("%B %d, %Y"), align='R', ln=1)
    
    # 2. Return Address
    if is_santa:
        # Force North Pole Address below Date
        pdf.set_x(140) 
        pdf.multi_cell(60, 5, "Santa Claus\n123 Elf Road\nNorth Pole, 88888", align='R')
    else:
        # Standard Top-Left
        pdf.set_xy(15, 15)
        pdf.multi_cell(0, 5, return_addr)

    # 3. Recipient Address
    recip_y = 80 if is_santa else 45
    pdf.set_xy(20, recip_y)
    pdf.set_font(addr_font, 'B', 12)
    pdf.multi_cell(0, 6, recipient_addr)# 4. Main Body Content
    pdf.set_xy(20, recip_y + 30)
    pdf.set_font(body_font, '', body_size)
    pdf.multi_cell(170, 8, content)

    # 5. Signature
    pdf.ln(20) 
    if is_santa:
        pdf.set_x(pdf.l_margin)
        pdf.set_font(font_map['hand'], '', 32)
        pdf.set_text_color(180, 20, 20) 
        pdf.cell(0, 10, "Love, Santa", align='C', ln=1)
    elif signature_path and os.path.exists(signature_path):
        try: pdf.image(signature_path, x=20, w=40)
        except: pass
    
    # 6. Footer
    pdf.set_y(-20)
    pdf.set_font('Helvetica', 'I', 8)
    pdf.set_text_color(100, 100, 100)
    footer = 'Official North Pole Mail' if is_santa else 'Dictated & Mailed via VerbaPost.com'
    pdf.cell(0, 10, footer, 0, 0, 'C')

    return pdf.output(dest="S")