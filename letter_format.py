from fpdf import FPDF
import os
import datetime

class LetterPDF(FPDF):
    def header(self):
        pass  # We handle the header manually in the body to control positioning

    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        # Arial italic 8
        self.set_font('Arial', 'I', 8)
        # Page number
        self.cell(0, 10, 'Page ' + str(self.page_no()) + '/{nb}', 0, 0, 'C')

def create_pdf(content, to_addr, from_addr, tier="Standard", signature_text=None, date_str=None):
    """
    Generates a PDF with the proper font and address layout.
    """
    pdf = LetterPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # --- 1. SETUP FONTS ---
    # Register the custom Typewriter font
    font_path = "type_right.ttf"
    has_custom_font = os.path.exists(font_path)
    
    if has_custom_font:
        pdf.add_font('TypeRight', '', font_path, uni=True)

    # Determine which font to use based on Tier
    if tier == "Heirloom" and has_custom_font:
        main_font = "TypeRight"
        header_font = "TypeRight"
        font_size = 12
        line_height = 6 # Tighter for typewriter feel
    elif tier == "Santa":
        main_font = "Times" # Or a script font if you have one
        header_font = "Times"
        font_size = 14
        line_height = 9
    else:
        # Standard / Civic
        main_font = "Times"
        header_font = "Helvetica" 
        font_size = 12
        line_height = 6

    # --- 2. RENDER FROM ADDRESS (Top Right) ---
    pdf.set_font(header_font, '', 10)
    
    # Helper to format address block
    def format_addr(addr_obj):
        # Handle dictionary or object inputs
        if isinstance(addr_obj, dict):
            name = addr_obj.get("name") or addr_obj.get("first_name", "")
            street = addr_obj.get("street") or addr_obj.get("address_line1", "")
            city = addr_obj.get("city", "")
            state = addr_obj.get("state", "")
            zip_code = addr_obj.get("zip_code") or addr_obj.get("zip", "")
        else:
            # Assume it's a StandardAddress object
            name = getattr(addr_obj, "name", "")
            street = getattr(addr_obj, "street", "")
            city = getattr(addr_obj, "city", "")
            state = getattr(addr_obj, "state", "")
            zip_code = getattr(addr_obj, "zip_code", "")
            
        lines = [name, street, f"{city}, {state} {zip_code}"]
        return [l for l in lines if l.strip()]

    from_lines = format_addr(from_addr)
    
    # Move to right side
    pdf.set_xy(120, 15) 
    for line in from_lines:
        pdf.cell(0, 5, line, ln=True, align='L') # Align L relative to the 120 margin
    
    # Add Date (Use passed date_str if available)
    pdf.set_xy(120, pdf.get_y() + 2)
    final_date = date_str if date_str else datetime.date.today().strftime("%B %d, %Y")
    pdf.cell(0, 5, final_date, ln=True, align='L')

    # --- 3. RENDER TO ADDRESS (Top Left - for Window Envelopes) ---
    pdf.set_xy(20, 45) # Standard window position
    to_lines = format_addr(to_addr)
    
    pdf.set_font(header_font, 'B', 11)
    for line in to_lines:
        pdf.cell(0, 5, line, ln=True)

    # --- 4. RENDER BODY CONTENT ---
    pdf.set_y(80) # Start body below the address area
    pdf.set_font(main_font, '', font_size)
    
    # Handle the "Dear X," if not present
    if "Dear" not in content[:20]:
        # Try to extract first name from recipient
        to_name = to_lines[0] if to_lines else "Friend"
        first_name = to_name.split()[0]
        pdf.multi_cell(0, line_height, f"Dear {first_name},\n\n")
        
    pdf.multi_cell(0, line_height, content)

    # --- 5. SIGNATURE (Fixed: No Double Signatures) ---
    
    # Check if user already typed a closing
    content_lower = content.lower().strip()
    common_closings = ["love,", "sincerely,", "best,", "warmly,", "yours,", "love mom", "love, mom"]
    has_closing = any(content_lower.endswith(s) for s in common_closings)
    
    if not has_closing:
        pdf.ln(15)
        
        # If a signature was provided in the UI form
        if signature_text:
            sign_off = signature_text
        else:
            # Fallback to From Name
            sender_name = from_lines[0] if from_lines else ""
            sign_off = "Sincerely,\n\n" + sender_name

        pdf.multi_cell(0, line_height, sign_off)

    # --- 6. OUTPUT ---
    # Save to temp path
    output_path = f"/tmp/letter_{int(datetime.datetime.now().timestamp())}.pdf"
    pdf.output(output_path)
    
    return output_path