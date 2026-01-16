from fpdf import FPDF
import os
import logging

logger = logging.getLogger(__name__)

# #10 Envelope Dimensions (Landscape)
ENV_W_MM = 241.3
ENV_H_MM = 104.8

def create_envelope(to_addr, from_addr):
    """
    Generates a #10 Envelope PDF using TypeRight font.
    """
    try:
        pdf = FPDF(orientation='L', unit='mm', format=(ENV_H_MM, ENV_W_MM))
        
        # --- FONT LOADING (FIXED PATH) ---
        font_family = 'Courier' # Safe fallback
        font_path = os.path.join("assets", "fonts", "type_right.ttf")
        
        if os.path.exists(font_path):
            try:
                pdf.add_font('TypeRight', '', font_path, uni=True)
                font_family = 'TypeRight'
            except: pass
        elif os.path.exists("type_right.ttf"): # Root fallback
             try:
                pdf.add_font('TypeRight', '', 'type_right.ttf', uni=True)
                font_family = 'TypeRight'
             except: pass
            
        pdf.add_page()
        pdf.set_font(font_family, '', 11)
        
        # --- HELPER: BUILD ADDRESS BLOCK ---
        def build_block(addr_dict):
            lines = []
            name = addr_dict.get('name') or addr_dict.get('company')
            if name: lines.append(str(name))
            
            street = addr_dict.get('address_line1')
            if street: lines.append(str(street))
            
            # City/State/Zip Logic
            city = addr_dict.get('city', '').strip()
            state = addr_dict.get('state', '').strip()
            zip_c = addr_dict.get('zip_code', '').strip()
            
            csz_line = ""
            if city: csz_line += city
            if state: 
                if csz_line: csz_line += f", {state}"
                else: csz_line = state
            if zip_c: csz_line += f" {zip_c}"
            
            # 🔴 FIX: Don't print empty lines or dangling commas
            clean_csz = csz_line.strip().strip(",").strip()
            if clean_csz: lines.append(clean_csz)
            
            return "\n".join(lines)
        
        # --- RETURN ADDRESS (Top Left) ---
        pdf.set_xy(15, 15)
        return_block = build_block(from_addr)
        pdf.multi_cell(80, 5, return_block)
        
        # --- DESTINATION ADDRESS (Center Right) ---
        pdf.set_xy(110, 50)
        dest_block = build_block(to_addr)
        pdf.multi_cell(100, 6, dest_block)
        
        # Output
        raw_output = pdf.output(dest='S')
        if isinstance(raw_output, str): return raw_output.encode('latin-1')
        elif isinstance(raw_output, bytearray): return bytes(raw_output)
        return raw_output

    except Exception as e:
        logger.error(f"Envelope Gen Error: {e}")
        return None