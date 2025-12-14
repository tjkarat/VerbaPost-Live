from fpdf import FPDF
import os

class PDF(FPDF):
    def header(self):
        pass
    def footer(self):
        pass

def create_pdf(text, sender_data, recipient_data, tier="Standard", font_choice="Standard"):
    """
    Generates a PDF with robust font handling and Unicode support.
    """
    # 1. Setup PDF (Portrait, mm, Letter size)
    pdf = PDF(orientation='P', unit='mm', format='Letter')
    
    # 2. Add Fonts (With Safety Check)
    # Define the mapping of "Friendly Name" -> "Filename.ttf"
    font_map = {
        "Caveat": "Caveat-Regular.ttf",
        "Great Vibes": "GreatVibes-Regular.ttf",
        "Indie Flower": "IndieFlower-Regular.ttf",
        "Schoolbell": "Schoolbell-Regular.ttf"
    }
    
    # Determine which font file to load
    target_font_file = font_map.get(font_choice)
    
    # Only try to load if it's not Standard AND the file actually exists
    loaded_custom_font = False
    if target_font_file and os.path.exists(target_font_file):
        try:
            # Register the font with FPDF (uni=True enables Unicode)
            pdf.add_font(font_choice, fname=target_font_file)
            loaded_custom_font = True
        except Exception as e:
            print(f"⚠️ Font Load Error ({target_font_file}): {e}")

    pdf.add_page()
    pdf.set_margins(25.4, 25.4, 25.4) # 1 inch margins

    # 3. Render Header (Standard Font for readability)
    pdf.set_font("Helvetica", size=10)
    
    # Return Address (Top Right)
    def safe_cell(txt, align='L', ln=True):
        # Cleans text to prevent latin-1 crashes in standard font
        clean_txt = str(txt).encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(0, 5, clean_txt, ln=ln, align=align)

    safe_cell(sender_data.get('name', ''), 'R')
    safe_cell(sender_data.get('street', ''), 'R')
    safe_cell(f"{sender_data.get('city', '')}, {sender_data.get('state', '')} {sender_data.get('zip', '')}", 'R')
    pdf.ln(10)

    # Recipient Address (Left)
    pdf.set_font("Helvetica", size=12)
    safe_cell(recipient_data.get('name', ''))
    safe_cell(recipient_data.get('street', ''))
    safe_cell(f"{recipient_data.get('city', '')}, {recipient_data.get('state', '')} {recipient_data.get('zip', '')}")
    pdf.ln(15)

    # 4. Render Body Text
    if loaded_custom_font:
        # Use the custom font we loaded successfully
        pdf.set_font(font_choice, size=14)
    else:
        # Fallback to standard if file missing or load failed
        pdf.set_font("Times", size=12)

    # Multi_cell handles text wrapping automatically
    # We purposefully do NOT encode/decode here to allow the custom font to handle Unicode
    pdf.multi_cell(0, 8, text)

    # 5. Output Bytes (Safe Method)
    try:
        # Returns bytearray directly, no .encode() needed
        return pdf.output(dest='S').encode('latin-1', 'replace') # Legacy FPDF compat
    except AttributeError:
        # Newer FPDF2 returns bytes directly
        return pdf.output()