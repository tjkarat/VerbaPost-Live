from fpdf import FPDF
import os
import requests
from datetime import datetime

# Font URLs
CAVEAT_URL = "https://github.com/google/fonts/raw/main/ofl/caveat/Caveat-Regular.ttf"
CJK_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

def ensure_fonts():
    """Downloads Caveat font if missing or corrupt."""
    font_path = "Caveat-Regular.ttf"
    
    # Check for corruption (files < 5KB are likely error pages)
    if os.path.exists(font_path):
        if os.path.getsize(font_path) < 5000:
            try: os.remove(font_path)
            except: pass
    
    # Download if missing
    if not os.path.exists(font_path):
        try:
            print("⬇️ Downloading Caveat Font...")
            r = requests.get(CAVEAT_URL, allow_redirects=True)
            if r.status_code == 200:
                with open(font_path, "wb") as f:
                    f.write(r.content)
            else:
                print(f"❌ Font Download Failed: {r.status_code}")
        except Exception as e:
            print(f"Font Download Error: {e}")

def create_pdf(content, recipient_addr, return_addr, is_heirloom, language, filename="letter.pdf", signature_path=None):
    ensure_fonts()
    
    pdf = FPDF()
    pdf.add_page()
    
    # --- FONT SELECTION ---
    font_family = 'Helvetica' # Default Fallback
    body_size = 12

    if language == "English":
        if os.path.exists("Caveat-Regular.ttf"):
            try:
                # Try loading. If file is bad, this throws exception.
                pdf.add_font('Caveat', '', "Caveat-Regular.ttf", uni=True)
                font_family = 'Caveat'
                body_size = 16 
            except Exception as e:
                print(f"⚠️ Font Error (Using Helvetica): {e}")
                # Delete corrupt file to retry next time
                try: os.remove("Caveat-Regular.ttf") 
                except: pass
                font_family = 'Helvetica'
                body_size = 12
    
    elif language in ["Japanese", "Chinese", "Korean"]:
        if os.path.exists(CJK_PATH):
            try:
                pdf.add_font('NotoCJK', '', CJK_PATH, uni=True)
                font_family = 'NotoCJK'
            except: pass
    
    # --- LAYOUT ---
    
    # 1. Return Address
    pdf.set_font('Helvetica', '', 10) 
    pdf.set_xy(10, 10)
    pdf.multi_cell(0, 5, return_addr)
    
    # 2. Recipient Address
    pdf.set_xy(20, 40)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.multi_cell(0, 6, recipient_addr)
    
    # 3. Date
    pdf.set_xy(160, 10)
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 10, datetime.now().strftime("%Y-%m-%d"), ln=True, align='R')
    
    # 4. Body Content
    pdf.set_xy(10, 80)
    pdf.set_font(font_family, '', body_size)
    pdf.multi_cell(0, 8, content)
    
    # 5. Signature
    if signature_path and os.path.exists(signature_path):
        pdf.ln(10)
        pdf.image(signature_path, w=40)
    
    # 6. Footer
    pdf.set_y(-20)
    pdf.set_font('Helvetica', 'I', 8)
    pdf.cell(0, 10, 'Dictated via VerbaPost.com', 0, 0, 'C')

    # Save
    save_path = f"/tmp/{filename}"
    pdf.output(save_path)
    return save_path