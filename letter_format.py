from fpdf import FPDF
import datetime

def _get_addr_field(data, keys):
    """
    Helper to find a value from a list of possible keys.
    Prevents blank lines if data keys vary (e.g. 'street' vs 'addressLine1').
    """
    if not data: return ""
    for k in keys:
        if k in data and data[k]:
            return str(data[k]).strip()
    return ""

def create_pdf(text, recipient_data, sender_data, tier="Standard", font_choice="Caveat", signature_text=""):
    """
    Generates a PDF for the physical letter.
    Robust against missing fonts and varying data keys.
    """
    
    class PDF(FPDF):
        def header(self):
            # Top margin
            self.ln(10)

        def footer(self):
            # 1.5cm from bottom
            self.set_y(-15)
            self.set_font("Helvetica", "I", 8)
            brand = "VerbaPost Legacy Service" if tier == "Legacy" else "VerbaPost"
            self.cell(0, 10, f"Sent via {brand}", 0, 0, "C")

    # 1. Setup PDF
    pdf = PDF()
    pdf.set_margins(25.4, 25.4, 25.4)  # 1-inch margins
    pdf.set_auto_page_break(auto=True, margin=25.4)
    pdf.add_page()

    # 2. Register Fonts (Safe Mode)
    # Ensure these files exist in root, otherwise fallback to Helvetica
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
            print(f"⚠️ Font {file_name} missing. Skipping.")

    # 3. Smart Data Mapping (The Fix)
    # Maps 'street' (Internal) -> 'addressLine1' (PostGrid) -> 'line1' (Civic)
    def extract_address(addr_dict):
        return {
            "name": _get_addr_field(addr_dict, ["name", "full_name", "firstName"]),
            "street": _get_addr_field(addr_dict, ["street", "address_line1", "addressLine1", "line1"]),
            "city": _get_addr_field(addr_dict, ["city", "address_city"]),
            "state": _get_addr_field(addr_dict, ["state", "address_state", "provinceOrState"]),
            "zip": _get_addr_field(addr_dict, ["zip", "zip_code", "address_zip", "postalOrZip"])
        }

    s = extract_address(sender_data)
    r = extract_address(recipient_data)

    # 4. Draw Sender (Return Address) - Top Left
    pdf.set_font("Helvetica", size=10)
    pdf.set_text_color(100, 100, 100) # Dark Gray
    
    pdf.cell(0, 5, s['name'], ln=True)
    pdf.cell(0, 5, s['street'], ln=True)
    pdf.cell(0, 5, f"{s['city']}, {s['state']} {s['zip']}", ln=True)
    
    # 5. Date
    pdf.ln(5)
    current_date = datetime.datetime.now().strftime("%B %d, %Y")
    pdf.cell(0, 5, current_date, ln=True)
    
    # 6. Draw Recipient (Window Envelope Position)
    pdf.ln(15)
    pdf.set_text_color(0, 0, 0) # Black
    
    pdf.cell(0, 5, r['name'], ln=True)
    pdf.cell(0, 5, r['street'], ln=True)
    pdf.cell(0, 5, f"{r['city']}, {r['state']} {r['zip']}", ln=True)

    # 7. Body Text
    pdf.ln(20)
    
    # Font Selection
    use_font = font_choice
    if use_font not in registered_fonts:
        use_font = "Helvetica" # Fallback
    
    # Sizing Tweaks
    base_size = 14
    if use_font == "Great Vibes": base_size = 16
    if use_font == "Schoolbell": base_size = 13
    
    pdf.set_font(use_font, size=base_size)
    
    # Safe Encoding
    safe_text = text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 8, safe_text)

    # 8. Signature
    pdf.ln(15)
    if signature_text:
        pdf.cell(0, 10, signature_text, ln=True)
    else:
        pdf.cell(0, 10, "Sincerely,", ln=True)
        pdf.cell(0, 10, s['name'], ln=True)

    return pdf.output(dest='S')