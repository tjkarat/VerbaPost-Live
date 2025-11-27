from fpdf import FPDF
import os
import requests
from datetime import datetime

# --- CONFIG ---
FONT_MAP = {
    "Caveat-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/caveat/Caveat-Regular.ttf",
}
# Fallback font path for Linux/Cloud (Asian Characters)
CJK_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

def ensure_fonts():
    for filename, url in FONT_MAP.items():
        if not os.path.exists(filename):
            try:
                r = requests.get(url, allow_redirects=True)
                if r.status_code == 200:
                    with open(filename, "wb") as f: f.write(r.content)
            except: pass

# --- CUSTOM PDF CLASS ---
class LetterPDF(FPDF):
    def __init__(self, is_santa=False, **kwargs):
        super().__init__(**kwargs)
        self.is_santa = is_santa

    def header(self):
        # This runs automatically every time a new page is added
        if self.is_santa:
            # Save current state to prevent infinite loops or layout shifts
            self.set_auto_page_break(False)
            
            # 1. Cream Background (Draw full page rect)
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
                # Fallback to Helvetica if fonts aren't loaded yet
                self.set_font("Helvetica", "B", 24)
                self.set_text_color(180, 20, 20) 
                self.cell(0, 10, "FROM THE DESK OF SANTA CLAUS", 0, 1, 'C')
                
                self.set_font("Helvetica", "I", 10)
                self.set_text_color(20, 100, 20) 
                self.cell(0, 5, "Official North Pole Correspondence | List Status: NICE", 0, 1, 'C')
                self.set_text_color(0, 0, 0) # Reset text color
            
            # Restore auto page break for the body content
            self.set_auto_page_break(True, margin=20)

def create_pdf(content, recipient_addr, return_addr, is_heirloom=False, language="English", signature_path=None, is_santa=False):
    print("--- PDF GENERATION STARTED ---")
    try:
        ensure_fonts()
        print("1. Fonts checked")
        
        # Initialize
        pdf = LetterPDF(is_santa=is_santa, format='Letter')
        pdf.set_auto_page_break(True, margin=20)
        print("2. PDF Class Initialized")
        
        # Fonts
        font_map = {}
        if os.path.exists("Caveat-Regular.ttf"):
            pdf.add_font('Caveat', '', 'Caveat-Regular.ttf', uni=True)
            font_map['hand'] = 'Caveat'
            print("3. Caveat Font Loaded")
        else:
            font_map['hand'] = 'Helvetica'
            print("3. Caveat Missing, using Helvetica")

        # Page Add (This triggers header)
        try:
            pdf.add_page()
            print("4. Page Added (Header Rendered)")
        except Exception as e:
            print(f"ERROR IN HEADER: {e}")
            raise e

        # Body Config
        body_font = font_map['hand'] if (is_heirloom or is_santa) else 'Helvetica'
        body_size = 18 if is_santa else 12
        
        # Content
        pdf.set_text_color(0, 0, 0)
        
        # Attempting to write text (Common failure point with emojis)
        try:
            # Recipient
            pdf.set_xy(20, 80 if is_santa else 45)
            pdf.set_font('Helvetica', 'B', 12)
            # Sanitize input to remove incompatible characters if strictly needed
            # recipient_addr = recipient_addr.encode('latin-1', 'replace').decode('latin-1') 
            pdf.multi_cell(0, 6, str(recipient_addr))
            print("5. Address Written")

            # Body
            pdf.set_xy(20, (80 if is_santa else 45) + 30)
            pdf.set_font(body_font, '', body_size)
            pdf.multi_cell(170, 8, str(content))
            print("6. Body Written")
        except Exception as e:
            print(f"ERROR WRITING TEXT: {e}")
            raise e

        # Signature
        pdf.ln(20) 
        if is_santa:
            pdf.set_x(pdf.l_margin)
            pdf.set_font(font_map.get('hand', 'Helvetica'), '', 32)
            pdf.set_text_color(180, 20, 20) 
            pdf.cell(0, 10, "Love, Santa", align='C', ln=1)
            print("7. Santa Sig Written")
        
        # Output
        print("8. Attempting Output...")
        # CRITICAL: Using 'S' returns a string. We must encode it safely.
        # 'latin-1' creates the PDF bytes. 'ignore' drops emojis instead of crashing.
        output_string = pdf.output(dest='S')
        byte_data = output_string.encode('latin-1', 'ignore') 
        
        print(f"9. Success! Generated {len(byte_data)} bytes")
        return byte_data

    except Exception as e:
        print(f"❌ FATAL PDF ERROR: {e}")
        # Return nothing so UI knows it failed
        return None