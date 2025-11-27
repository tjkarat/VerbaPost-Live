from fpdf import FPDF
import os
import requests
from datetime import datetime

# --- CONFIG ---
# Map font filenames to their Google Fonts URLs for automatic downloading.
FONT_MAP = {
    "Caveat-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/caveat/Caveat-Regular.ttf",
}

# Path to a CJK (Chinese/Japanese/Korean) font if available on the system.
CJK_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

def ensure_fonts():
    """
    Checks if required font files exist locally. If not, downloads them.
    """
    for filename, url in FONT_MAP.items():
        if not os.path.exists(filename):
            try:
                print(f"Downloading {filename}...")
                r = requests.get(url, allow_redirects=True)
                if r.status_code == 200:
                    with open(filename, "wb") as f:
                        f.write(r.content)
                    print("Download complete.")
            except Exception as e:
                print(f"Failed to download font {filename}: {e}")

def create_pdf(content, recipient_addr, return_addr, is_heirloom, language="English", signature_path=None, is_santa=False):
    """
    Generates a PDF letter. If is_santa is True, it draws a custom festive design 
    programmatically to avoid copyright issues with external images.
    """
    # 1. Ensure external fonts are ready
    ensure_fonts()
    
    # 2. Initialize PDF setup
    pdf = FPDF(format='Letter')
    pdf.set_auto_page_break(True, margin=20)
    
    # 3. Register Fonts
    font_map = {}
    if os.path.exists("Caveat-Regular.ttf"):
        pdf.add_font('Caveat', '', 'Caveat-Regular.ttf', uni=True)
        font_map['hand'] = 'Caveat'
    else:
        font_map['hand'] = 'Helvetica'

    if os.path.exists(CJK_PATH):
        try:
            pdf.add_font('NotoCJK', '', CJK_PATH, uni=True)
            font_map['cjk'] = 'NotoCJK'
        except: pass

    # 4. Create Page
    pdf.add_page()
    
    # --- CUSTOM SANTA DESIGN (PROGRAMMATIC) ---
    if is_santa:
        # A. Background Color (Vintage Cream)
        pdf.set_fill_color(252, 247, 235) 
        # Draw full page rectangle
        pdf.rect(0, 0, 215.9, 279.4, 'F')
        
        # B. Festive Borders
        # Outer Red Border
        pdf.set_line_width(2)
        pdf.set_draw_color(180, 20, 20) # Christmas Red
        pdf.rect(5, 5, 205.9, 269.4)
        
        # Inner Green Border
        pdf.set_line_width(1)
        pdf.set_draw_color(20, 100, 20) # Christmas Green
        pdf.rect(8, 8, 199.9, 263.4)
        
        # C. North Pole Header
        pdf.set_y(20)
        pdf.set_font("Helvetica", "B", 24)
        pdf.set_text_color(180, 20, 20) # Red Text
        pdf.cell(0, 10, "FROM THE DESK OF SANTA CLAUS", 0, 1, 'C')
        
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(20, 100, 20) # Green Text
        pdf.cell(0, 5, "Official North Pole Correspondence | List Status: NICE", 0, 1, 'C')# 5. Determine Font Styles
    if language in ["Japanese", "Chinese", "Korean"] and 'cjk' in font_map:
        body_font = font_map['cjk']
        addr_font = font_map['cjk']
        body_size = 12
    else:
        body_font = font_map['hand'] if (is_heirloom or is_santa) else 'Helvetica'
        addr_font = 'Helvetica' 
        body_size = 18 if is_santa else (16 if body_font == 'Caveat' else 12)

    # 6. Place Content Elements
    pdf.set_text_color(0, 0, 0) # Reset to black for main text

    # A. Return Address (Skip for Santa as we have the header)
    if not is_santa:
        pdf.set_font(addr_font, '', 10)
        pdf.set_xy(15, 15)
        pdf.multi_cell(0, 5, return_addr)
    
    # B. Date
    # Move date down if Santa header exists
    date_y = 50 if is_santa else 15 
    pdf.set_xy(150, date_y)
    pdf.set_font(addr_font, '', 10)
    pdf.cell(50, 0, datetime.now().strftime("%B %d, %Y"), align='R')
    
    # C. Recipient Address
    recip_y = 60 if is_santa else 45
    pdf.set_xy(20, recip_y)
    pdf.set_font(addr_font, 'B', 12)
    pdf.multi_cell(0, 6, recipient_addr)
    
    # D. Main Body Content
    body_y = 90 if is_santa else 80
    pdf.set_xy(20, body_y)
    pdf.set_font(body_font, '', body_size)
    pdf.multi_cell(170, 8, content)
    
    # E. Signature
    pdf.ln(20) # Add space before signature
    
    if is_santa:
        # Santa Signature (Centered)
        pdf.set_x(pdf.l_margin)
        pdf.set_font(font_map['hand'], '', 32)
        pdf.set_text_color(180, 20, 20) # Sign in Red
        pdf.cell(0, 10, "Love, Santa", align='C', ln=1)
        pdf.set_text_color(0, 0, 0) # Reset
        
    elif signature_path and os.path.exists(signature_path):
        try:
            pdf.image(signature_path, x=20, w=40)
        except: pass
    
    # 7. Footer
    pdf.set_y(-20) 
    pdf.set_font('Helvetica', 'I', 8)
    footer = 'Official North Pole Mail' if is_santa else 'Dictated & Mailed via VerbaPost.com'
    pdf.cell(0, 10, footer, 0, 0, 'C')

    # 8. Return PDF bytes
    return pdf.output(dest="S")