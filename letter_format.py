from fpdf import FPDF
import os
import requests
from datetime import datetime
import re
import logging

# Configure Logger
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
FONT_MAP = {
    "Caveat-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/caveat/Caveat-Regular.ttf",
    "NotoSansSC-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/notosanssc/NotoSansSC-Regular.ttf",
    "NotoSansJP-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/notosansjp/NotoSansJP-Regular.ttf",
    "NotoSansKR-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/notosanskr/NotoSansKR-Regular.ttf",
}

def ensure_fonts():
    for filename, url in FONT_MAP.items():
        if not os.path.exists(filename):
            try:
                r = requests.get(url, allow_redirects=True)
                if r.status_code == 200:
                    with open(filename, "wb") as f: f.write(r.content)
            except Exception as e:
                logger.error(f"Font Download Error: {e}")

def detect_language(text):
    if not text: return ('Helvetica', None)
    if re.search(r'[\u3040-\u30ff]', text): return ('NotoSansJP', 'NotoSansJP-Regular.ttf')
    if re.search(r'[\uac00-\ud7af]', text): return ('NotoSansKR', 'NotoSansKR-Regular.ttf')
    if re.search(r'[\u4e00-\u9fff]', text): return ('NotoSansSC', 'NotoSansSC-Regular.ttf')
    return ('Helvetica', None)

def sanitize_text(text, is_cjk=False):
    if not isinstance(text, str): return str(text)
    replacements = {'\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"', '\u2013': '-', '\u2014': '-'}
    for k, v in replacements.items(): text = text.replace(k, v)
    
    if is_cjk: return text 
    else:
        try: return text.encode('latin-1', 'ignore').decode('latin-1')
        except: return text

class LetterPDF(FPDF):
    def __init__(self, is_santa=False, **kwargs):
        super().__init__(**kwargs)
        self.is_santa = is_santa

    def header(self):
        if self.is_santa:
            self.set_auto_page_break(False)
            self.set_fill_color(252, 247, 235) 
            self.rect(0, 0, 215.9, 279.4, 'F')
            self.set_line_width(2); self.set_draw_color(180, 20, 20); self.rect(5, 5, 205.9, 269.4)
            self.set_line_width(1); self.set_draw_color(20, 100, 20); self.rect(8, 8, 199.9, 263.4)
            
            if self.page_no() == 1:
                self.set_y(20); self.set_font("Helvetica", "B", 24); self.set_text_color(180, 20, 20) 
                self.cell(0, 10, "FROM THE DESK OF SANTA CLAUS", 0, 1, 'C')
                self.set_font("Helvetica", "I", 10); self.set_text_color(20, 100, 20) 
                self.cell(0, 5, "Official North Pole Correspondence | List Status: NICE", 0, 1, 'C')
                self.set_text_color(0, 0, 0)
            self.set_auto_page_break(True, margin=20)

    def footer(self):
        self.set_y(-15); self.set_font('Helvetica', 'I', 8); self.set_text_color(100, 100, 100)
        text = 'Official North Pole Mail' if self.is_santa else 'Dictated & Mailed via VerbaPost.com'
        self.cell(0, 10, text, 0, 0, 'C')

def create_pdf(content, recipient_addr, return_addr, is_heirloom=False, language="English", signature_path=None, is_santa=False):
    try:
        ensure_fonts()
        pdf = LetterPDF(is_santa=is_santa, format='Letter')
        pdf.set_auto_page_break(True, margin=20)
        
        if os.path.exists("Caveat-Regular.ttf"): pdf.add_font('Caveat', '', 'Caveat-Regular.ttf')
        target_font_name, target_font_file = detect_language(content)
        is_cjk = target_font_name.startswith("Noto")
        
        if is_cjk and target_font_file and os.path.exists(target_font_file):
            pdf.add_font(target_font_name, '', target_font_file)
        else: target_font_name = 'Helvetica'; is_cjk = False

        if is_cjk: body_font = target_font_name
        elif is_heirloom or is_santa: body_font = 'Caveat'
        else: body_font = 'Helvetica'
            
        body_size = 14 if is_cjk else (18 if is_santa else 12)
        
        pdf.add_page(); pdf.set_text_color(0, 0, 0)
        
        is_standard = not (is_heirloom or is_santa)
        if is_standard:
            pdf.set_xy(20, 100); pdf.set_xy(140, 15); pdf.set_font('Helvetica', '', 10)
            pdf.cell(60, 5, datetime.now().strftime("%B %d, %Y"), align='R', ln=1); pdf.set_xy(20, 100)
        else:
            date_y = 50 if is_santa else 15
            pdf.set_xy(140, date_y); pdf.set_font('Helvetica', '', 10)
            pdf.cell(60, 5, datetime.now().strftime("%B %d, %Y"), align='R', ln=1)
            
            if is_santa:
                pdf.set_x(140); pdf.multi_cell(60, 5, "Santa Claus\n123 Elf Road\nNorth Pole, 88888", align='R')
            else:
                pdf.set_xy(15, 15); pdf.multi_cell(0, 5, sanitize_text(return_addr, is_cjk))

            recip_y = 80 if is_santa else 45
            pdf.set_xy(20, recip_y); pdf.set_font('Helvetica', 'B', 12)
            pdf.multi_cell(0, 6, sanitize_text(recipient_addr, is_cjk))
            pdf.set_xy(20, recip_y + 30)

        pdf.set_font(body_font, '', body_size)
        safe_content = sanitize_text(content, is_cjk)
        if not safe_content or len(safe_content.strip()) == 0:
            safe_content = "[ERROR: No Content Provided. Please return to editor.]"; pdf.set_text_color(255, 0, 0) 
            
        pdf.multi_cell(170, 8, safe_content); pdf.set_text_color(0, 0, 0)
        pdf.ln(20) 
        
        if is_santa:
            pdf.set_x(pdf.l_margin); sig_font = 'Caveat' if not is_cjk else 'Helvetica' 
            pdf.set_font(sig_font, '', 32); pdf.set_text_color(180, 20, 20) 
            pdf.cell(0, 10, "Love, Santa", align='C', ln=1)
        elif signature_path and os.path.exists(signature_path):
            try: pdf.image(signature_path, x=20, w=40)
            except: pass
        
        raw_output = pdf.output(dest='S')
        if isinstance(raw_output, (bytes, bytearray)): return bytes(raw_output)
        elif isinstance(raw_output, str): return raw_output.encode('latin-1', 'ignore')
        else: return bytes(raw_output)

    except Exception as e:
        logger.error(f"PDF Generation Failed: {e}", exc_info=True)
        return None

if __name__ == "__main__":
    ensure_fonts()