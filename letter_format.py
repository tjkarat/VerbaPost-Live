from fpdf import FPDF
import os

class PDF(FPDF):
    def header(self):
        pass  # No header for now
    def footer(self):
        pass  # No footer for now

def create_pdf(text, sender_data, recipient_data, tier="Standard", font_choice="Caveat"):
    """
    Generates a PDF with custom font support.
    font_choice options: 'Caveat', 'GreatVibes', 'IndieFlower', 'Schoolbell'
    """
    pdf = PDF()
    pdf.add_page()
    
    # --- FONT REGISTRATION ---
    # We map friendly names to filenames. 
    # Assumes fonts are in the root directory or specific folder.
    font_map = {
        "Caveat": "Caveat-Regular.ttf",
        "Great Vibes": "GreatVibes-Regular.ttf",
        "Indie Flower": "IndieFlower-Regular.ttf",
        "Schoolbell": "Schoolbell-Regular.ttf",
        "Standard": "Helvetica"  # Fallback
    }
    
    selected_font_file = font_map.get(font_choice, "Caveat-Regular.ttf")
    
    # 1. Try to load the custom font
    try:
        if font_choice != "Standard":
            # Register the font (must exist in root dir)
            pdf.add_font(font_choice, '', selected_font_file, uni=True)
            pdf.set_font(font_choice, '', 14)
        else:
            pdf.set_font("Helvetica", '', 12)
    except Exception as e:
        print(f"Font loading failed ({selected_font_file}): {e}")
        pdf.set_font("Helvetica", '', 12) # Fallback if file missing

    # --- LAYOUT LOGIC ---
    line_height = 8 if font_choice != "Standard" else 6
    
    # 2. Add Content
    # Return Address
    pdf.set_font_size(10)
    pdf.cell(0, 5, f"{sender_data.get('name','')}", ln=True, align='R')
    pdf.cell(0, 5, f"{sender_data.get('street','')}", ln=True, align='R')
    pdf.cell(0, 5, f"{sender_data.get('city','')}, {sender_data.get('state','')} {sender_data.get('zip','')}", ln=True, align='R')
    pdf.ln(10)

    # Date (Optional, or auto-generated)
    # pdf.cell(0, 5, "December 14, 2025", ln=True) 
    # pdf.ln(10)

    # Recipient Address
    pdf.set_font_size(12)
    pdf.cell(0, 6, f"{recipient_data.get('name','')}", ln=True)
    pdf.cell(0, 6, f"{recipient_data.get('street','')}", ln=True)
    pdf.cell(0, 6, f"{recipient_data.get('city','')}, {recipient_data.get('state','')} {recipient_data.get('zip','')}", ln=True)
    pdf.ln(15)

    # Body Text (Restore handwriting font size)
    if font_choice != "Standard":
        pdf.set_font(font_choice, '', 14)
    
    # Handle UTF-8 safely
    pdf.multi_cell(0, line_height, text)

    return pdf.output(dest='S').encode('latin-1', 'ignore')