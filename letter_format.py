from fpdf import FPDF
import os
import datetime

class LetterPDF(FPDF):
    def __init__(self):
        super().__init__(format='Letter')

    def header(self):
        pass

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, 'Page ' + str(self.page_no()) + '/{nb}', 0, 0, 'C')

def create_pdf(content, to_addr, from_addr, tier="Standard", signature_text=None, date_str=None, clean_render=False):
    """
    clean_render (bool): If True, hides addresses (used when sending to PostGrid 
                         with 'insert_blank_page' to avoid double addresses).
    """
    pdf = LetterPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    
    # --- 1. SETUP FONTS ---
    font_path = "type_right.ttf"
    has_custom_font = os.path.exists(font_path)
    if has_custom_font:
        try: pdf.add_font('TypeRight', '', font_path, uni=True)
        except: has_custom_font = False

    if tier == "Heirloom" and has_custom_font:
        main_font, header_font = "TypeRight", "TypeRight"
        font_size, line_height, bold_style = 12, 6, ''
    elif tier == "Santa":
        main_font, header_font = "Times", "Times"
        font_size, line_height, bold_style = 14, 9, 'B'
    else:
        main_font, header_font = "Times", "Helvetica"
        font_size, line_height, bold_style = 12, 6, 'B'

    def format_addr(addr_obj):
        if not addr_obj: return []
        if isinstance(addr_obj, dict):
            name = addr_obj.get("name") or addr_obj.get("full_name") or ""
            street = addr_obj.get("street") or addr_obj.get("address_line1") or ""
            city = addr_obj.get("city", "")
            state = addr_obj.get("state", "")
            zip_code = addr_obj.get("zip_code") or addr_obj.get("zip") or ""
        else:
            name = getattr(addr_obj, "name", "")
            street = getattr(addr_obj, "street", "")
            city = getattr(addr_obj, "city", "")
            state = getattr(addr_obj, "state", "")
            zip_code = getattr(addr_obj, "zip_code", "")
        lines = [name, street, f"{city}, {state} {zip_code}"]
        return [l for l in lines if l.strip()]

    # --- 2. RENDER ADDRESSES (Conditional) ---
    if not clean_render:
        # Sender
        from_lines = format_addr(from_addr)
        pdf.set_font(header_font, '', 10)
        pdf.set_xy(20, 15)
        for line in from_lines: pdf.cell(0, 5, line, ln=True, align='L')
        
        # Recipient
        pdf.set_xy(20, 50)
        to_lines = format_addr(to_addr)
        pdf.set_font(header_font, bold_style, 11)
        for line in to_lines: pdf.cell(0, 5, line, ln=True)
    else:
        # Just grab name for the "Dear X" logic later
        to_lines = format_addr(to_addr)
        from_lines = format_addr(from_addr)

    # Date (Always show)
    pdf.set_font(header_font, '', 10)
    pdf.set_xy(120, 20)
    final_date = date_str if date_str and "Unknown" not in date_str else datetime.date.today().strftime("%B %d, %Y")
    pdf.cell(0, 5, final_date, ln=True, align='L')

    # --- 3. RENDER BODY ---
    # Safe zone starts at 105mm to clear windows
    current_y = pdf.get_y()
    safe_body_start = max(105, current_y + 25) 
    pdf.set_y(safe_body_start)
    pdf.set_font(main_font, '', font_size)
    
    clean_content = content.strip()
    
    # Auto-Salutation
    if tier != "Heirloom" and not clean_content.lower().startswith("dear"):
        to_name = to_lines[0] if to_lines else "Friend"
        first_name = to_name.split()[0]
        pdf.multi_cell(0, line_height, f"Dear {first_name},\n\n")
        
    pdf.multi_cell(0, line_height, clean_content)

    # --- 4. SIGNATURE ---
    content_lower = clean_content.lower()[-50:] 
    common_closings = ["love,", "sincerely,", "best,", "warmly,", "yours,", "love mom", "love, mom", "mom", "dad"]
    has_signoff = any(c in content_lower for c in common_closings)
    
    if not has_signoff:
        pdf.ln(15)
        sign_off = signature_text if signature_text else f"Sincerely,\n\n{from_lines[0] if from_lines else ''}"
        pdf.multi_cell(0, line_height, sign_off)

    try: return bytes(pdf.output())
    except TypeError: return pdf.output(dest='S').encode('latin-1')