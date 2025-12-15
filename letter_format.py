from fpdf import FPDF
import datetime

def create_pdf(text, recipient_data, sender_data, tier="Standard", font_choice="Caveat", signature_text=""):
    """
    Generates a PDF for the physical letter.
    
    Args:
        text (str): The body of the letter.
        recipient_data (dict): To address.
        sender_data (dict): From address.
        tier (str): Current tier (Standard, Legacy, etc).
        font_choice (str): One of "Caveat", "Great Vibes", "Indie Flower", "Schoolbell".
        signature_text (str): The sign-off text.
        
    Returns:
        bytes: The PDF binary data.
    """
    
    class PDF(FPDF):
        def header(self):
            # Clean, ample top margin for professional look
            self.ln(10)

        def footer(self):
            # Positioning at 1.5 cm from bottom
            self.set_y(-15)
            self.set_font("Helvetica", "I", 8)
            # Tier-based footer branding
            brand = "VerbaPost Legacy Service" if tier == "Legacy" else "VerbaPost"
            self.cell(0, 10, f"Sent via {brand}", 0, 0, "C")

    # 1. Initialize PDF
    pdf = PDF()
    pdf.set_margins(25.4, 25.4, 25.4)  # 1-inch margins
    pdf.set_auto_page_break(auto=True, margin=25.4)
    pdf.add_page()

    # 2. Register Custom Fonts
    # NOTE: Ensure these .ttf files are in your root directory!
    fonts_to_register = [
        ("Caveat", "Caveat-Regular.ttf"),
        ("Great Vibes", "GreatVibes-Regular.ttf"),
        ("Indie Flower", "IndieFlower-Regular.ttf"),
        ("Schoolbell", "Schoolbell-Regular.ttf")
    ]

    registered_fonts = []
    
    for font_name, file_name in fonts_to_register:
        try:
            pdf.add_font(font_name, style="", fname=file_name)
            registered_fonts.append(font_name)
        except Exception:
            print(f"⚠️ Warning: Font file '{file_name}' not found. Skipping.")

    # 3. Determine Font to Use
    # If selected font didn't load, fallback to Caveat, then Helvetica
    use_font = font_choice
    if use_font not in registered_fonts:
        if "Caveat" in registered_fonts:
            use_font = "Caveat"
        else:
            use_font = "Helvetica"

    # 4. Draw Sender Address (Top Left, Small)
    pdf.set_font("Helvetica", size=10)
    pdf.set_text_color(100, 100, 100) # Dark Gray
    
    s_name = sender_data.get("name", "")
    s_street = sender_data.get("street", "")
    s_city = sender_data.get("city", "")
    s_state = sender_data.get("state", "")
    s_zip = sender_data.get("zip", "")
    
    pdf.cell(0, 5, s_name, ln=True)
    pdf.cell(0, 5, s_street, ln=True)
    pdf.cell(0, 5, f"{s_city}, {s_state} {s_zip}", ln=True)
    
    # 5. Draw Date
    pdf.ln(5)
    current_date = datetime.datetime.now().strftime("%B %d, %Y")
    pdf.cell(0, 5, current_date, ln=True)
    
    # 6. Draw Recipient Block (Standard Position for Window Envelopes)
    pdf.ln(15)
    pdf.set_text_color(0, 0, 0) # Black
    
    r_name = recipient_data.get("name", "")
    r_street = recipient_data.get("street", "")
    r_city = recipient_data.get("city", "")
    r_state = recipient_data.get("state", "")
    r_zip = recipient_data.get("zip", "")
    
    pdf.cell(0, 5, r_name, ln=True)
    pdf.cell(0, 5, r_street, ln=True)
    pdf.cell(0, 5, f"{r_city}, {r_state} {r_zip}", ln=True)

    # 7. Write Body Content
    pdf.ln(20)
    
    # Adjust sizing based on font quirks
    base_size = 14
    if use_font == "Great Vibes": base_size = 16  # Runs small
    if use_font == "Schoolbell": base_size = 13   # Runs large
    
    pdf.set_font(use_font, size=base_size)
    
    # Handles encoding specific characters if necessary (latin-1 is standard for FPDF)
    safe_text = text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 8, safe_text)

    # 8. Signature
    pdf.ln(15)
    if signature_text:
        pdf.cell(0, 10, signature_text, ln=True)
    else:
        pdf.cell(0, 10, "Sincerely,", ln=True)
        pdf.cell(0, 10, s_name, ln=True)

    # 9. Return Bytes
    return pdf.output(dest='S')