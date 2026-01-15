from fpdf import FPDF
import os
import logging

logger = logging.getLogger(__name__)

# #10 Envelope Dimensions (Landscape)
ENV_W_MM = 241.3
ENV_H_MM = 104.8

def create_envelope(to_addr, from_addr):
    """
    Generates a #10 Envelope PDF in Typewriter font.
    """
    try:
        pdf = FPDF(orientation='L', unit='mm', format=(ENV_H_MM, ENV_W_MM))
        
        # Load Font
        font_family = 'Courier'
        if os.path.exists("type_right.ttf"):
            try:
                pdf.add_font('TypeRight', '', 'type_right.ttf', uni=True)
                font_family = 'TypeRight'
            except: pass
            
        pdf.add_page()
        pdf.set_font(font_family, '', 11)
        
        # --- RETURN ADDRESS (Top Left) ---
        # Advisor / Sender
        f_name = from_addr.get('name') or from_addr.get('company', '')
        f_street = from_addr.get('address_line1', '')
        f_city = from_addr.get('city', '')
        f_state = from_addr.get('state', '')
        f_zip = from_addr.get('zip_code', '')
        
        # Position: 15mm from left, 15mm from top
        pdf.set_xy(15, 15)
        return_block = f"{f_name}\n{f_street}\n{f_city}, {f_state} {f_zip}"
        pdf.multi_cell(80, 5, return_block)
        
        # --- DESTINATION ADDRESS (Center Right) ---
        # Heir / Recipient
        t_name = to_addr.get('name', '')
        t_street = to_addr.get('address_line1', '')
        t_city = to_addr.get('city', '')
        t_state = to_addr.get('state', '')
        t_zip = to_addr.get('zip_code', '')
        
        # Position: 110mm from left (roughly middle), 60mm from top
        pdf.set_xy(110, 50)
        dest_block = f"{t_name}\n{t_street}\n{t_city}, {t_state} {t_zip}"
        
        # Make destination slightly larger/bolder logic if needed, 
        # but same font size is standard for typewriters.
        pdf.multi_cell(100, 6, dest_block)
        
        # Output
        raw_output = pdf.output(dest='S')
        if isinstance(raw_output, str): return raw_output.encode('latin-1')
        elif isinstance(raw_output, bytearray): return bytes(raw_output)
        return raw_output

    except Exception as e:
        logger.error(f"Envelope Gen Error: {e}")
        return None
