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
# This is specific to Linux/Debian environments.
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
    Generates a PDF letter based on inputs.
    """
    # 1. Ensure external fonts are ready
    ensure_fonts()
    
    # 2. Initialize PDF setup
    pdf = FPDF(format='Letter')
    pdf.set_auto_page_break(True, margin=20)
    
    # 3. Register Fonts
    font_map = {}
    # Add handwriting font if available, else fallback to standard
    if os.path.exists("Caveat-Regular.ttf"):
        pdf.add_font('Caveat', '', 'Caveat-Regular.ttf', uni=True)
        font_map['hand'] = 'Caveat'
    else:
        font_map['hand'] = 'Helvetica'

    # Add CJK font if available
    if os.path.exists(CJK_PATH):
        try:
            pdf.add_font('NotoCJK', '', CJK_PATH, uni=True)
            font_map['cjk'] = 'NotoCJK'
        except: pass

    # 4. Create Page & Apply Background
    pdf.add_page()
    
    # If Santa tier and bg image exists, apply it full page
    if is_santa and os.path.exists("santa_bg.jpg"):
        # x=0, y=0 puts it top-left. w=215.9, h=279.4 is standard Letter size in mm.
        pdf.image("santa_bg.jpg", x=0, y=0, w=215.9, h=279.4)

    # 5. Determine Font Styles based on language and tier
    if language in ["Japanese", "Chinese", "Korean"] and 'cjk' in font_map:
        # Use CJK font for everything if Asian language selected
        body_font = font_map['cjk']
        addr_font = font_map['cjk']
        body_size = 12
    else:
        # Standard logic
        # Use handwriting font for Heirloom/Santa, else standard Helvetica
        body_font = font_map['hand'] if (is_heirloom or is_santa) else 'Helvetica'
        addr_font = 'Helvetica' 
        # Santa gets bigger text, Caveat gets slightly bigger than Helvetica
        body_size = 18 if is_santa else (16 if body_font == 'Caveat' else 12)

    # 6. Place Content Elements
    
    # A. Return Address (Top Left) - Skip for Santa
    if not is_santa:
        pdf.set_font(addr_font, '', 10)
        pdf.set_xy(15, 15) # standard margin positions
        pdf.multi_cell(0, 5, return_addr)
    
    # B. Date (Top Right)
    date_y = 55 if is_santa else 15 # Move date down if Santa BG exists
    pdf.set_xy(150, date_y)
    pdf.set_font(addr_font, '', 10)
    # Align right
    pdf.cell(50, 0, datetime.now().strftime("%B %d, %Y"), align='R')
    
    # C. Recipient Address (Below Return/Date)
    recip_y = 65 if is_santa else 45 # Adjust Y position based on tier
    pdf.set_xy(20, recip_y)
    pdf.set_font(addr_font, 'B', 12)
    pdf.multi_cell(0, 6, recipient_addr)
    
    # D. Main Body Content
    body_y = 100 if is_santa else 80 # Adjust Y position
    pdf.set_xy(20, body_y)
    pdf.set_font(body_font, '', body_size)
    # multi_cell(width, line_height, text)
    pdf.multi_cell(170, 8, content)
    
    # E. Signature
    pdf.ln(20) # Add space before signature
    
    if is_santa:
        # SANTA SIGNATURE FIX: Center aligned
        pdf.set_x(pdf.l_margin) # Reset to left margin to ensure centering is correct across page
        pdf.set_font(font_map['hand'], '', 28) # Bigger font
        # width=0 spans to right margin, align='C' centers text
        pdf.cell(0, 10, "Love, Santa", align='C', ln=1)
    elif signature_path and os.path.exists(signature_path):
        # Place user's drawn signature image
        try:
            # x=20 matches left margin of body text. w=40 scales image width.
            pdf.image(signature_path, x=20, w=40)
        except: pass
    
    # 7. Footer (Bottom Center)
    pdf.set_y(-20) # Move to 20mm from bottom
    pdf.set_font('Helvetica', 'I', 8)
    footer = 'North Pole Official Mail' if is_santa else 'Dictated & Mailed via VerbaPost.com'
    # Center aligned cell spanning page width
    pdf.cell(0, 10, footer, 0, 0, 'C')

    # 8. Return PDF as bytes string (dest="S")
    return pdf.output(dest="S")