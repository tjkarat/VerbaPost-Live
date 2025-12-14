from fpdf import FPDF
import os

class LetterPDF(FPDF):
    def header(self):
        # Header is usually blank for these letters to look personal
        pass

    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128)
        self.cell(0, 10, "Sent via VerbaPost", align="C")

def create_pdf(body_text, to_addr, from_addr, tier="Standard", font_choice=None):
    """
    Generates a PDF byte array.
    Robustly handles string vs bytearray return types to fix 'encode' errors.
    """
    pdf = LetterPDF()
    pdf.add_page()
    
    # --- 1. Fonts Setup ---
    chosen_font_name = "Helvetica" # Default
    
    # Safe font loading logic
    try:
        # If specific font requested (Legacy flow)
        if font_choice and "Caveat" in font_choice and os.path.exists("Caveat-Regular.ttf"):
            pdf.add_font("Caveat", "", "Caveat-Regular.ttf")
            chosen_font_name = "Caveat"
        # Or if tier defaults to handwriting (Standard/Heirloom)
        elif tier in ["Standard", "Heirloom"] and os.path.exists("Caveat-Regular.ttf"):
            pdf.add_font("Caveat", "", "Caveat-Regular.ttf")
            chosen_font_name = "Caveat"
    except Exception as e:
        print(f"Font loading error: {e}")
    
    # --- 2. Return Address ---
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100) # Grey
    
    # Handle object vs dict input safely
    s_name = from_addr.get("name") if isinstance(from_addr, dict) else getattr(from_addr, "name", "")
    s_str = from_addr.get("street") if isinstance(from_addr, dict) else getattr(from_addr, "street", "")
    s_city = from_addr.get("city") if isinstance(from_addr, dict) else getattr(from_addr, "city", "")
    s_state = from_addr.get("state") if isinstance(from_addr, dict) else getattr(from_addr, "state", "")
    s_zip = from_addr.get("zip") if isinstance(from_addr, dict) else getattr(from_addr, "zip_code", "")
    
    pdf.multi_cell(0, 5, f"{s_name}\n{s_str}\n{s_city}, {s_state} {s_zip}")
    pdf.ln(10)
    
    # --- 3. Date ---
    from datetime import datetime
    date_str = datetime.now().strftime("%B %d, %Y")
    pdf.cell(0, 10, date_str, ln=True)
    pdf.ln(5)

    # --- 4. Recipient ---
    pdf.set_text_color(0, 0, 0) # Black
    r_name = to_addr.get("name") if isinstance(to_addr, dict) else getattr(to_addr, "name", "")
    r_str = to_addr.get("street") if isinstance(to_addr, dict) else getattr(to_addr, "street", "")
    r_city = to_addr.get("city") if isinstance(to_addr, dict) else getattr(to_addr, "city", "")
    r_state = to_addr.get("state") if isinstance(to_addr, dict) else getattr(to_addr, "state", "")
    r_zip = to_addr.get("zip") if isinstance(to_addr, dict) else getattr(to_addr, "zip_code", "")
    
    pdf.multi_cell(0, 5, f"{r_name}\n{r_str}\n{r_city}, {r_state} {r_zip}")
    pdf.ln(15)

    # --- 5. Body ---
    if chosen_font_name == "Caveat":
        pdf.set_font("Caveat", "", 16)
    else:
        pdf.set_font("Times", "", 12)
        
    pdf.multi_cell(0, 8, body_text)
    
    # --- 6. Signature ---
    pdf.ln(15)
    pdf.cell(0, 10, "Sincerely,", ln=True)
    pdf.ln(15)
    pdf.cell(0, 10, s_name, ln=True)

    # --- 7. CRITICAL OUTPUT FIX ---
    try:
        # FPDF2 returns bytearray, Old FPDF returns string
        raw_output = pdf.output(dest='S')
        
        if isinstance(raw_output, str):
            return raw_output.encode('latin-1')
        else:
            return bytes(raw_output) # Convert to immutable bytes
            
    except Exception as e:
        print(f"PDF Output Error: {e}")
        return b""