from fpdf import FPDF
import os

def create_pdf(text, address_data, tier="Standard"):
    """
    Generates a PDF binary.
    """
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # --- FONT SELECTION ---
    # Fallback to standard fonts if custom ones aren't loaded
    font_family = "Times" if tier == "Heirloom" else "Arial"
    pdf.set_font(font_family, '', 12)

    # --- ADDRESS BLOCK ---
    # Top Left: Sender
    pdf.set_font_size(10)
    pdf.set_text_color(100, 100, 100) # Grey
    
    sender_lines = [
        address_data.get('name', ''),
        address_data.get('street', ''),
        f"{address_data.get('city', '')}, {address_data.get('state', '')} {address_data.get('zip', '')}"
    ]
    
    for line in sender_lines:
        if line.strip(): pdf.cell(0, 5, line, ln=True)

    pdf.ln(10)

    # --- RECIPIENT BLOCK (Window Envelope Position) ---
    # Move to X=100mm, Y=45mm (approx)
    pdf.set_y(45)
    pdf.set_x(100)
    pdf.set_text_color(0, 0, 0) # Black
    
    # Handle Civic (List of Reps) vs Standard (Single Recipient)
    if tier == "Civic":
        recip_lines = ["Honorable Representatives", "United States Congress", "Washington, DC 20510"]
    else:
        recip_lines = [
            address_data.get('r_name', ''),
            address_data.get('r_street', ''),
            f"{address_data.get('r_city', '')}, {address_data.get('r_state', '')} {address_data.get('r_zip', '')}"
        ]

    for line in recip_lines:
        pdf.set_x(100)
        if line.strip(): pdf.cell(0, 5, line, ln=True)

    # --- BODY TEXT ---
    pdf.set_y(90) # Start body below window
    pdf.set_font_size(12)
    
    # Clean text to prevent latin-1 errors
    safe_text = text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 6, safe_text)

    # --- OUTPUT ---
    # FIX: Check type before encoding to prevent crash
    try:
        res = pdf.output(dest='S')
        if isinstance(res, str):
            return res.encode('latin-1')
        return res # Already bytes/bytearray
    except Exception:
        return pdf.output()