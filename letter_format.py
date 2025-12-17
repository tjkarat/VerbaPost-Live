from fpdf import FPDF
import os
import datetime

class LetterPDF(FPDF):
    def __init__(self):
        # FIX 1: Explicitly set format='Letter' (8.5x11) for PostGrid US compatibility
        # FPDF defaults to A4 (8.27x11.69), which causes the PostGrid error.
        super().__init__(format='Letter')

    def header(self):
        # We handle the header manually in the body to control positioning exactly
        pass

    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        # Arial italic 8
        self.set_font('Arial', 'I', 8)
        # Page number
        self.cell(0, 10, 'Page ' + str(self.page_no()) + '/{nb}', 0, 0, 'C')

def create_pdf(content, to_addr, from_addr, tier="Standard", signature_text=None, date_str=None):
    """
    Generates a US LETTER sized PDF with the proper font and address layout.
    """
    pdf = LetterPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # --- 1. SETUP FONTS ---
    # We look for the custom font in the current directory
    font_path = "type_right.ttf"
    has_custom_font = os.path.exists(font_path)
    
    if has_custom_font:
        # 'uni=True' is critical for special characters
        try:
            pdf.add_font('TypeRight', '', font_path, uni=True)
        except Exception as e:
            print(f"Error loading font: {e}")
            has_custom_font = False
    else:
        # Fallback if the file is missing in Production
        print(f"WARNING: Font {font_path} not found. Falling back to Standard.")

    # Determine which font to use based on Tier
    # We also define 'bold_style' here to prevent crashes on custom fonts that lack bold versions
    if tier == "Heirloom" and has_custom_font:
        main_font = "TypeRight"
        header_font = "TypeRight"
        font_size = 12
        line_height = 6 # Tighter line height for typewriter feel
        bold_style = '' # FIX: Custom TTF often doesn't have a Bold variant loaded, so we force Regular
    elif tier == "Santa":
        main_font = "Times" # Or a script font if you have one
        header_font = "Times"
        font_size = 14
        line_height = 9
        bold_style = 'B'
    else:
        # Standard / Civic tiers
        main_font = "Times"
        header_font = "Helvetica" 
        font_size = 12
        line_height = 6
        bold_style = 'B' # Standard fonts support fake bolding

    # --- 2. RENDER FROM ADDRESS (Top Right) ---
    
    # Helper to safely format address block from either Dict or Object
    def format_addr(addr_obj):
        if not addr_obj: return []
        
        # Handle dictionary inputs (from Address Book)
        if isinstance(addr_obj, dict):
            name = addr_obj.get("name") or addr_obj.get("first_name", "")
            street = addr_obj.get("street") or addr_obj.get("address_line1", "")
            city = addr_obj.get("city", "")
            state = addr_obj.get("state", "")
            zip_code = addr_obj.get("zip_code") or addr_obj.get("zip", "")
        else:
            # Handle Class Object inputs (from Database/StandardAddress)
            name = getattr(addr_obj, "name", "")
            street = getattr(addr_obj, "street", "")
            city = getattr(addr_obj, "city", "")
            state = getattr(addr_obj, "state", "")
            zip_code = getattr(addr_obj, "zip_code", "")
            
        lines = [name, street, f"{city}, {state} {zip_code}"]
        return [l for l in lines if l.strip()]

    # Format the sender address
    from_lines = format_addr(from_addr)
    
    # Set font for addresses
    pdf.set_font(header_font, '', 10)
    
    # Move to right side (120mm from left margin)
    pdf.set_xy(120, 15) 
    for line in from_lines:
        pdf.cell(0, 5, line, ln=True, align='L') # Align L relative to the 120 margin
    
    # Add Date
    pdf.set_xy(120, pdf.get_y() + 2)
    # Use the passed date string, or fallback to Today if it's missing or "Unknown"
    final_date = date_str if date_str and "Unknown" not in date_str else datetime.date.today().strftime("%B %d, %Y")
    pdf.cell(0, 5, final_date, ln=True, align='L')

    # --- 3. RENDER TO ADDRESS (Top Left - for Window Envelopes) ---
    pdf.set_xy(20, 45) # Standard window envelope position
    to_lines = format_addr(to_addr)
    
    # Use the bold_style variable (either 'B' or '') to prevent crashing
    pdf.set_font(header_font, bold_style, 11)
    
    for line in to_lines:
        pdf.cell(0, 5, line, ln=True)

    # --- 4. RENDER BODY CONTENT ---
    
    # FIX 2: Collision Prevention
    # Instead of hardcoding 80, use the maximum of 80 OR the current Y + gap
    current_y = pdf.get_y()
    safe_body_start = max(80, current_y + 20)
    
    pdf.set_y(safe_body_start) 
    pdf.set_font(main_font, '', font_size)
    
    # Handle the "Dear X," if not present in the user's text
    clean_content = content.strip()
    if not clean_content.lower().startswith("dear"):
        # Try to extract first name from recipient
        to_name = to_lines[0] if to_lines else "Friend"
        first_name = to_name.split()[0]
        pdf.multi_cell(0, line_height, f"Dear {first_name},\n\n")
        
    pdf.multi_cell(0, line_height, clean_content)

    # --- 5. SIGNATURE ---
    # Smart Logic: Don't add a signature if the user already typed "Love, Mom"
    
    content_lower = clean_content.lower()[-50:] # Only check the end
    common_closings = ["love,", "sincerely,", "best,", "warmly,", "yours,", "love mom", "love, mom", "mom", "dad"]
    
    has_signoff = False
    for closing in common_closings:
        if closing in content_lower:
            has_signoff = True
            break
    
    if not has_signoff:
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