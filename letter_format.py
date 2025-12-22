from fpdf import FPDF
import os
import datetime

class LetterPDF(FPDF):
    def __init__(self):
        # Explicitly set format='Letter' (8.5x11) for PostGrid US compatibility
        super().__init__(format='Letter')

    def header(self):
        pass

    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128) # Gray color
        
        # --- NEW BRANDING FOOTER ---
        # Line 1: Page Number
        self.cell(0, 5, 'Page ' + str(self.page_no()) + '/{nb}', 0, 1, 'C')
        # Line 2: Attribution
        self.cell(0, 5, 'Dictated and written by VerbaPost.com', 0, 0, 'C')

def create_pdf(content, to_addr, from_addr, tier="Standard", signature_text=None, date_str=None, clean_render=False):
    """
    Generates a US LETTER sized PDF and returns the BYTES (not the path).
    layout: standard_double_window compatible (Left/Left addresses).
    clean_render (bool): If True, hides addresses (used for PostGrid 'insert_blank_page').
    """
    pdf = LetterPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # --- 1. SETUP FONTS ---
    font_path = "type_right.ttf"
    has_custom_font = os.path.exists(font_path)
    
    if has_custom_font:
        try:
            pdf.add_font('TypeRight', '', font_path, uni=True)
        except Exception as e:
            print(f"Error loading font: {e}")
            has_custom_font = False
    else:
        # Just a log warning, not fatal
        pass

    if tier == "Heirloom" and has_custom_font:
        main_font = "TypeRight"
        header_font = "TypeRight"
        font_size = 12
        line_height = 6 
        bold_style = '' 
    elif tier == "Santa":
        main_font = "Times" 
        header_font = "Times"
        font_size = 14
        line_height = 9
        bold_style = 'B'
    else:
        main_font = "Times"
        header_font = "Helvetica" 
        font_size = 12
        line_height = 6
        bold_style = 'B' 

    # --- HELPER: FORMAT ADDRESS ---
    def format_addr(addr_obj):
        if not addr_obj: return []
        if isinstance(addr_obj, dict):
            name = addr_obj.get("name") or addr_obj.get("first_name", "") or addr_obj.get("full_name", "")
            street = addr_obj.get("street") or addr_obj.get("address_line1", "")
            city = addr_obj.get("city", "")
            state = addr_obj.get("state", "")
            zip_code = addr_obj.get("zip_code") or addr_obj.get("zip", "")
        else:
            name = getattr(addr_obj, "name", "")
            street = getattr(addr_obj, "street", "")
            city = getattr(addr_obj, "city", "")
            state = getattr(addr_obj, "state", "")
            zip_code = getattr(addr_obj, "zip_code", "")
            
        lines = [name, street, f"{city}, {state} {zip_code}"]
        return [l for l in lines if l.strip()]

    # Prep address lines (needed for logic later even if not printed)
    to_lines = format_addr(to_addr)
    from_lines = format_addr(from_addr)

    # --- 2 & 3. RENDER ADDRESSES (CONDITIONAL) ---
    if not clean_render:
        # FROM ADDRESS (TOP LEFT WINDOW)
        # Moved from X=120 to X=20 to match the standard double window
        pdf.set_font(header_font, '', 10)
        pdf.set_xy(20, 15) 
        for line in from_lines:
            pdf.cell(0, 5, line, ln=True, align='L') 

        # TO ADDRESS (MIDDLE LEFT WINDOW)
        # Moved Y from 45 to 50 to center vertically in the window
        pdf.set_xy(20, 50) 
        pdf.set_font(header_font, bold_style, 11)
        for line in to_lines:
            pdf.cell(0, 5, line, ln=True)
    
    # Render Date (Moved to Right to balance layout) - Always render date
    pdf.set_font(header_font, '', 10)
    pdf.set_xy(120, 20)
    final_date = date_str if date_str and "Unknown" not in date_str else datetime.date.today().strftime("%B %d, %Y")
    pdf.cell(0, 5, final_date, ln=True, align='L')

    # --- 4. RENDER BODY (SAFE ZONE) ---
    # Moved safe_body_start to 105mm. This clears both windows and the first fold.
    current_y = pdf.get_y()
    safe_body_start = max(105, current_y + 25) 
    pdf.set_y(safe_body_start) 
    pdf.set_font(main_font, '', font_size)
    
    clean_content = content.strip()
    
    # Auto-Insert "Dear X" if missing (except for Heirloom)
    if tier != "Heirloom" and not clean_content.lower().startswith("dear"):
        to_name = to_lines[0] if to_lines else "Friend"
        first_name = to_name.split()[0]
        pdf.multi_cell(0, line_height, f"Dear {first_name},\n\n")
        
    pdf.multi_cell(0, line_height, clean_content)

    # --- 5. SIGNATURE ---
    content_lower = clean_content.lower()[-50:] 
    common_closings = ["love,", "sincerely,", "best,", "warmly,", "yours,", "love mom", "love, mom", "mom", "dad"]
    has_signoff = any(c in content_lower for c in common_closings)
    
    if not has_signoff:
        pdf.ln(15)
        if signature_text:
            sign_off = signature_text
        else:
            sender_name = from_lines[0] if from_lines else ""
            sign_off = "Sincerely,\n\n" + sender_name
        pdf.multi_cell(0, line_height, sign_off)

    # --- 6. OUTPUT ---
    try:
        # FPDF2 style
        return bytes(pdf.output())
    except TypeError:
        # FPDF 1.7 / PyFPDF style
        return pdf.output(dest='S').encode('latin-1')