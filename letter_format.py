from fpdf import FPDF
import os

class LetterPDF(FPDF):
    def header(self):
        # Header is usually blank for these letters to look personal
        pass

    def footer(self):
        # Simple footer
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128)
        self.cell(0, 10, "Sent via VerbaPost", align="C")

def create_pdf(body_text, to_addr, from_addr, tier="Standard", font_choice=None):
    """
    Generates a PDF byte array.
    Automatically includes a signature block for all standard letter types.
    """
    pdf = LetterPDF()
    pdf.add_page()
    
    # --- 1. Fonts Setup ---
    # Determine which font family to use (Caveat is default handwriting)
    # If font_choice is passed (from Legacy UI), use it.
    
    chosen_font_name = "Helvetica" # Default fallback
    
    # Map common names to file paths if you have them, otherwise use Helvetica/Times
    # We assume 'Caveat-Regular.ttf' exists in root as per earlier context
    if font_choice and "Caveat" in font_choice:
        if os.path.exists("Caveat-Regular.ttf"):
            pdf.add_font("Caveat", "", "Caveat-Regular.ttf")
            chosen_font_name = "Caveat"
    elif tier in ["Heirloom", "Standard", "Legacy"] and os.path.exists("Caveat-Regular.ttf"):
        # Default to Caveat for these tiers if not specified
        pdf.add_font("Caveat", "", "Caveat-Regular.ttf")
        chosen_font_name = "Caveat"
    
    # --- 2. Return Address (Top Left) ---
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100) # Grey
    
    # Handle dict vs Object input safely
    s_name = from_addr.get("name") if isinstance(from_addr, dict) else from_addr.name
    s_str = from_addr.get("street") if isinstance(from_addr, dict) else from_addr.street
    s_city = from_addr.get("city") if isinstance(from_addr, dict) else from_addr.city
    s_state = from_addr.get("state") if isinstance(from_addr, dict) else from_addr.state
    s_zip = from_addr.get("zip") if isinstance(from_addr, dict) else from_addr.zip_code
    
    pdf.multi_cell(0, 5, f"{s_name}\n{s_str}\n{s_city}, {s_state} {s_zip}")
    pdf.ln(10)
    
    # --- 3. Date ---
    from datetime import datetime
    date_str = datetime.now().strftime("%B %d, %Y")
    pdf.cell(0, 10, date_str, ln=True)
    pdf.ln(5)

    # --- 4. Recipient Address ---
    pdf.set_text_color(0, 0, 0) # Black
    
    r_name = to_addr.get("name") if isinstance(to_addr, dict) else to_addr.name
    r_str = to_addr.get("street") if isinstance(to_addr, dict) else to_addr.street
    r_city = to_addr.get("city") if isinstance(to_addr, dict) else to_addr.city
    r_state = to_addr.get("state") if isinstance(to_addr, dict) else to_addr.state
    r_zip = to_addr.get("zip") if isinstance(to_addr, dict) else to_addr.zip_code
    
    pdf.multi_cell(0, 5, f"{r_name}\n{r_str}\n{r_city}, {r_state} {r_zip}")
    pdf.ln(15)

    # --- 5. Letter Body ---
    if chosen_font_name == "Caveat":
        pdf.set_font("Caveat", "", 16)
    else:
        pdf.set_font("Times", "", 12)
        
    pdf.multi_cell(0, 8, body_text)
    
    # --- 6. SIGNATURE BLOCK ---
    # Always add this unless explicitly disabled
    pdf.ln(15) # Add space after body
    
    # Closing
    pdf.cell(0, 10, "Sincerely,", ln=True)
    
    # Space for manual signature
    pdf.ln(15) 
    
    # Typed Name
    pdf.cell(0, 10, s_name, ln=True)

    # Output as immutable bytes (fixes bytearray error)
    return bytes(pdf.output(dest='S').encode('latin-1'))