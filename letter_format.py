from fpdf import FPDF
import os
import requests
from datetime import datetime

# --- FONT CONFIGURATION ---
# We map the local filename to the download URL
FONT_MAP = {
    "Caveat-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/caveat/Caveat-Regular.ttf",
    "Roboto-Regular.ttf": "https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Regular.ttf",
    "Roboto-Bold.ttf": "https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Bold.ttf"
}

# Fallback for Asian characters (if available on system)
CJK_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

def ensure_fonts():
    """Checks for fonts locally; downloads them if missing."""
    for filename, url in FONT_MAP.items():
        if not os.path.exists(filename):
            try:
                print(f"⬇️ Downloading font: {filename}...")
                r = requests.get(url, allow_redirects=True)
                if r.status_code == 200:
                    with open(filename, "wb") as f:
                        f.write(r.content)
            except Exception as e:
                print(f"⚠️ Font download failed for {filename}: {e}")

def create_pdf(content, recipient_addr, return_addr, is_heirloom, language="English", signature_path=None):
    # 1. Ensure fonts exist
    ensure_fonts()
    
    # 2. Init PDF (Letter Size)
    pdf = FPDF(format='Letter')
    pdf.set_auto_page_break(True, margin=20)
    
    # 3. Register Fonts
    # We use specific keys 'Caveat' and 'Roboto' to refer to them later
    fonts_loaded = {}
    
    # Handwriting (Caveat)
    if os.path.exists("Caveat-Regular.ttf"):
        pdf.add_font('Caveat', '', 'Caveat-Regular.ttf', uni=True)
        fonts_loaded['hand'] = 'Caveat'
    else:
        fonts_loaded['hand'] = 'Helvetica' # Fallback

    # Standard (Roboto)
    if os.path.exists("Roboto-Regular.ttf") and os.path.exists("Roboto-Bold.ttf"):
        pdf.add_font('Roboto', '', 'Roboto-Regular.ttf', uni=True)
        pdf.add_font('Roboto', 'B', 'Roboto-Bold.ttf', uni=True)
        fonts_loaded['sans'] = 'Roboto'
    else:
        fonts_loaded['sans'] = 'Helvetica' # Fallback

    # CJK (Asian Characters)
    if os.path.exists(CJK_PATH):
        try:
            pdf.add_font('NotoCJK', '', CJK_PATH, uni=True)
            fonts_loaded['cjk'] = 'NotoCJK'
        except: pass

    pdf.add_page()
    
    # Select Logic
    if language in ["Japanese", "Chinese", "Korean"] and 'cjk' in fonts_loaded:
        body_font = fonts_loaded['cjk']
        addr_font = fonts_loaded['cjk']
        body_size = 12
    else:
        body_font = fonts_loaded['hand'] 
        addr_font = fonts_loaded['sans'] 
        # Caveat needs to be larger to be readable
        body_size = 16 if body_font == 'Caveat' else 12

    # --- CONTENT ---
    
    # 1. Return Address (Top Left) - Absolute Positioning
    pdf.set_font(addr_font, '', 10)
    current_y = 15
    for line in return_addr.split('\n'):
        if line.strip():
            pdf.text(12, current_y, line.strip())
            current_y += 5
    
    # 2. Date (Top Right)
    pdf.set_xy(150, 15)
    pdf.cell(50, 0, datetime.now().strftime("%B %d, %Y"), align='R')
    
    # 3. Recipient (Window Envelope Position)
    # Standard #10 Window starts around Y=40mm
    pdf.set_font(addr_font, 'B', 12)
    current_y = 45 
    for line in recipient_addr.split('\n'):
        if line.strip():
            pdf.text(20, current_y, line.strip())
            current_y += 6
    
    # 4. Body Text
    pdf.set_xy(15, 80) 
    pdf.set_font(body_font, '', body_size)
    pdf.multi_cell(0, 8, content)
    
    # 5. Signature Image
    if signature_path and os.path.exists(signature_path):
        pdf.ln(10)
        # Check if space remains, else add page
        if pdf.get_y() > 230: pdf.add_page()
        try: 
            pdf.image(signature_path, w=40)
        except: pass
    
    # 6. Footer
    pdf.set_y(-20)
    pdf.set_font(addr_font, '', 8)
    pdf.cell(0, 10, 'Dictated & Mailed via VerbaPost.com', 0, 0, 'C')

    # Return Raw Bytes (No encoding, fixes crash)
    return pdf.output(dest="S")