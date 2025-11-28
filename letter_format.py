from fpdf import FPDF
import os
import requests
from datetime import datetime
import streamlit as st

# --- CONFIG ---
# Direct raw link to the font file
FONT_MAP = {
    "Caveat-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/caveat/Caveat-Regular.ttf",
}

def ensure_fonts():
    """Downloads the font to the local container if missing."""
    for filename, url in FONT_MAP.items():
        if not os.path.exists(filename):
            try:
                print(f"⬇️ Downloading font: {filename}...")
                r = requests.get(url, allow_redirects=True)
                if r.status_code == 200:
                    with open(filename, "wb") as f: 
                        f.write(r.content)
                    print("✅ Font downloaded.")
                else:
                    print(f"❌ Font download failed: {r.status_code}")
            except Exception as e: 
                print(f"❌ Font Error: {e}")

def sanitize_text(text):
    """
    Replaces incompatible unicode characters (smart quotes, dashes) 
    with ASCII equivalents to prevent PDF crashes.
    """
    if not isinstance(text, str): return str(text)
    
    replacements = {
        '\u2018': "'", # Left single quote
        '\u2019': "'", # Right single quote
        '\u201c': '"', # Left double quote
        '\u201d': '"', # Right double quote
        '\u2013': '-', # En dash
        '\u2014': '-'  # Em dash
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    
    # Encode/Decode ensures we strip anything else that might break Latin-1
    return text.encode('latin-1', 'replace').decode('latin-1')

# --- CUSTOM PDF CLASS ---
class LetterPDF(FPDF):
    def __init__(self, is_santa=False, **kwargs):
        super().__init__(**kwargs)
        self.is_santa = is_santa

    def header(self):
        if self.is_santa:
            self.set_auto_page_break(False)
            
            # 1. Background
            self.set_fill_color(252, 247, 235) 
            self.rect(0, 0, 215.9, 279.4, 'F')
            
            # 2. Borders
            self.set_line_width(2)
            self.set_draw_color(180, 20, 20) 
            self.rect(5, 5, 205.9, 269.4)
            
            self.set_line_width(1)
            self.set_draw_color(20, 100, 20) 
            self.rect(8, 8, 199.9, 263.4)
            
            # 3. Header Text (Page 1 Only)
            if self.page_no() == 1:
                self.set_y(20)
                # Use standard font for header to be safe
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
        
        # Initialize
        pdf = LetterPDF(is_santa=is_santa, format='Letter')
        pdf.set_auto_page_break(True, margin=20)
        
        # --- FONT REGISTRATION (THE FIX) ---
        font_map = {}
        if os.path.exists("Caveat-Regular.ttf") and os.path.getsize("Caveat-Regular.ttf") > 0:
            try:
                # REMOVED 'uni=True' (This was crashing fpdf2)
                pdf.add_font('Caveat', '', 'Caveat-Regular.ttf')
                font_map['hand'] = 'Caveat'
            except Exception as e: 
                print(f"⚠️ Font Load Error: {e}")
                font_map['hand'] = 'Helvetica'
        else:
            font_map['hand'] = 'Helvetica'

        # Page Add
        pdf.add_page()

        # Config
        body_font = font_map['hand'] if (is_heirloom or is_santa) else 'Helvetica'
        body_size = 18 if is_santa else 12
        
        # --- CONTENT PLACEMENT ---
        pdf.set_text_color(0, 0, 0)
        
        is_standard = not (is_heirloom or is_santa)

        if is_standard:
            # --- STANDARD MODE (PostGrid overlay space) ---
            pdf.set_xy(20, 100) 
            
            # Date (Top Right)
            pdf.set_xy(140, 15)
            pdf.set_font('Helvetica', '', 10)
            pdf.cell(60, 5, datetime.now().strftime("%B %d, %Y"), align='R', ln=1)
            
            # Reset cursor
            pdf.set_xy(20, 100)

        else:
            # --- HEIRLOOM / SANTA MODE (Manual Print) ---
            
            # 1. Date
            date_y = 50 if is_santa else 15
            pdf.set_xy(140, date_y)
            pdf.set_font('Helvetica', '', 10)
            pdf.cell(60, 5, datetime.now().strftime("%B %d, %Y"), align='R', ln=1)
            
            # 2. Return Address
            if is_santa:
                pdf.set_x(140) 
                pdf.multi_cell(60, 5, "Santa Claus\n123 Elf Road\nNorth Pole, 88888", align='R')
            else:
                pdf.set_xy(15, 15)
                pdf.multi_cell(0, 5, sanitize_text(return_addr))

            # 3. Recipient Address
            recip_y = 80 if is_santa else 45
            pdf.set_xy(20, recip_y)
            pdf.set_font('Helvetica', 'B', 12)
            pdf.multi_cell(0, 6, sanitize_text(recipient_addr))
            
            # Set cursor for body
            pdf.set_xy(20, recip_y + 30)

        # 4. Main Body Content
        pdf.set_font(body_font, '', body_size)
        safe_content = sanitize_text(content)
        pdf.multi_cell(170, 8, safe_content)

        # 5. Signature
        pdf.ln(20) 
        if is_santa:
            pdf.set_x(pdf.l_margin)
            # Try to use the hand font for signature, fallback to standard if missing
            sig_font = font_map.get('hand', 'Helvetica')
            pdf.set_font(sig_font, '', 32)
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

        # --- OUTPUT ---
        raw_output = pdf.output(dest='S') # 'S' returns bytes in FPDF2
        return bytes(raw_output)

    except Exception as e:
        st.error(f"INTERNAL PDF ENGINE ERROR: {e}")
        print(f"PDF Error: {e}")
        return None