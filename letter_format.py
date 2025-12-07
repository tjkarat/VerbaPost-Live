from fpdf import FPDF
import os
import requests
from datetime import datetime
import re

# --- CONFIGURATION ---
# We map specific scripts to Google Fonts (Open Font License)
FONT_MAP = {
    "Caveat-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/caveat/Caveat-Regular.ttf",
    "NotoSansSC-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/notosanssc/NotoSansSC-Regular.ttf", # Chinese
    "NotoSansJP-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/notosansjp/NotoSansJP-Regular.ttf", # Japanese
    "NotoSansKR-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/notosanskr/NotoSansKR-Regular.ttf", # Korean
}

def ensure_fonts():
    """Downloads missing fonts on startup."""
    for filename, url in FONT_MAP.items():
        if not os.path.exists(filename):
            try:
                print(f"⬇️ Downloading font: {filename}...")
                r = requests.get(url, allow_redirects=True)
                if r.status_code == 200:
                    with open(filename, "wb") as f: f.write(r.content)
                    print(f"✅ Saved {filename}")
            except Exception as e:
                print(f"❌ Font Download Error: {e}")

def detect_language(text):
    """
    Analyzes text to determine the best font.
    Returns: ('font_name', 'font_file')
    """
    if not text: return ('Helvetica', None)
    
    # 1. Check for Japanese (Hiragana/Katakana)
    if re.search(r'[\u3040-\u30ff]', text):
        return ('NotoSansJP', 'NotoSansJP-Regular.ttf')
    
    # 2. Check for Korean (Hangul)
    if re.search(r'[\uac00-\ud7af]', text):
        return ('NotoSansKR', 'NotoSansKR-Regular.ttf')
        
    # 3. Check for Chinese (Hanzi)
    # Note: Japanese uses Kanji (Hanzi), so we check Kana first. 
    # If we see CJK Unified Ideographs but no Kana, assume Chinese.
    if re.search(r'[\u4e00-\u9fff]', text):
        return ('NotoSansSC', 'NotoSansSC-Regular.ttf')
        
    # 4. Default to Western
    return ('Helvetica', None)

def sanitize_text(text, is_cjk=False):
    """
    Cleans text. If CJK, we DO NOT strip unicode.
    If Western, we replace smart quotes to prevent Latin-1 errors.
    """
    if not isinstance(text, str): return str(text)
    
    # Common cleanup for all languages
    replacements = {
        '\u2018': "'", '\u2019': "'", 
        '\u201c': '"', '\u201d': '"',
        '\u2013': '-', '\u2014': '-'
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    
    if is_cjk:
        return text # Return raw Unicode for CJK fonts
    else:
        # For Helvetica, force Latin-1 compatible
        return text.encode('latin-1', 'replace').decode('latin-1')

# --- CUSTOM PDF CLASS ---
class LetterPDF(FPDF):
    def __init__(self, is_santa=False, **kwargs):
        super().__init__(**kwargs)
        self.is_santa = is_santa

    def header(self):
        if self.is_santa:
            self.set_auto_page_break(False)
            
            # Background & Borders
            self.set_fill_color(252, 247, 235) 
            self.rect(0, 0, 215.9, 279.4, 'F')
            self.set_line_width(2)
            self.set_draw_color(180, 20, 20) 
            self.rect(5, 5, 205.9, 269.4)
            self.set_line_width(1)
            self.set_draw_color(20, 100, 20) 
            self.rect(8, 8, 199.9, 263.4)
            
            # Header Text
            if self.page_no() == 1:
                self.set_y(20)
                self.set_font("Helvetica", "B", 24)
                self.set_text_color(180, 20, 20) 
                self.cell(0, 10, "FROM THE DESK OF SANTA CLAUS", 0, 1, 'C')
                
                self.set_font("Helvetica", "I", 10)
                self.set_text_color(20, 100, 20) 
                self.cell(0, 5, "Official North Pole Correspondence | List Status: NICE", 0, 1, 'C')
                self.set_text_color(0, 0, 0)
            
            self.set_auto_page_break(True, margin=20)

def create_pdf(content, recipient_addr, return_addr, is_heirloom=False, language="English", signature_path=None, is_santa=False):
    try:
        ensure_fonts()
        
        pdf = LetterPDF(is_santa=is_santa, format='Letter')
        pdf.set_auto_page_break(True, margin=20)
        
        # --- FONT LOGIC ---
        # 1. Register Handwriting Font (Caveat) - Western Only
        if os.path.exists("Caveat-Regular.ttf"):
            pdf.add_font('Caveat', '', 'Caveat-Regular.ttf')
        
        # 2. Detect Language from Content
        target_font_name, target_font_file = detect_language(content)
        is_cjk = target_font_name.startswith("Noto")
        
        # 3. Register CJK Font if needed
        if is_cjk and target_font_file:
            if os.path.exists(target_font_file):
                pdf.add_font(target_font_name, '', target_font_file)
            else:
                # Fallback if download failed
                target_font_name = 'Helvetica'
                is_cjk = False

        # 4. Select Body Font
        if is_cjk:
            body_font = target_font_name
        elif is_heirloom or is_santa:
            body_font = 'Caveat'
        else:
            body_font = 'Helvetica'
            
        body_size = 14 if is_cjk else (18 if is_santa else 12)
        
        # --- START CONTENT ---
        pdf.add_page()
        pdf.set_text_color(0, 0, 0)
        
        is_standard = not (is_heirloom or is_santa)

        if is_standard:
            # Standard Mode (PostGrid)
            pdf.set_xy(20, 100)
            pdf.set_xy(140, 15)
            pdf.set_font('Helvetica', '', 10)
            pdf.cell(60, 5, datetime.now().strftime("%B %d, %Y"), align='R', ln=1)
            pdf.set_xy(20, 100)
        else:
            # Heirloom/Santa (Manual)
            date_y = 50 if is_santa else 15
            pdf.set_xy(140, date_y)
            pdf.set_font('Helvetica', '', 10)
            pdf.cell(60, 5, datetime.now().strftime("%B %d, %Y"), align='R', ln=1)
            
            # Return Address
            if is_santa:
                pdf.set_x(140) 
                pdf.multi_cell(60, 5, "Santa Claus\n123 Elf Road\nNorth Pole, 88888", align='R')
            else:
                pdf.set_xy(15, 15)
                pdf.multi_cell(0, 5, sanitize_text(return_addr, is_cjk))

            # Recipient Address
            recip_y = 80 if is_santa else 45
            pdf.set_xy(20, recip_y)
            pdf.set_font('Helvetica', 'B', 12)
            pdf.multi_cell(0, 6, sanitize_text(recipient_addr, is_cjk))
            
            pdf.set_xy(20, recip_y + 30)

        # Body
        pdf.set_font(body_font, '', body_size)
        safe_content = sanitize_text(content, is_cjk)
        
        # --- SAFETY FIX ---
        if not safe_content or len(safe_content.strip()) == 0:
            safe_content = "[ERROR: No Content Provided. Please return to editor.]"
            pdf.set_text_color(255, 0, 0) # Red text warning
            
        pdf.multi_cell(170, 8, safe_content)
        pdf.set_text_color(0, 0, 0)

        # Signature
        pdf.ln(20) 
        if is_santa:
            pdf.set_x(pdf.l_margin)
            # Use Western handwriting for "Santa" sig or Helvetica if missing
            sig_font = 'Caveat' if not is_cjk else 'Helvetica' 
            pdf.set_font(sig_font, '', 32)
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

        # --- OUTPUT ---
        raw_output = pdf.output(dest='S')
        if isinstance(raw_output, (bytes, bytearray)):
            return bytes(raw_output)
        elif isinstance(raw_output, str):
            return raw_output.encode('latin-1', 'ignore')
        else:
            return bytes(raw_output)

    except Exception as e:
        print(f"PDF Generation Error: {e}")
        return None

if __name__ == "__main__":
    ensure_fonts()