from fpdf import FPDF
import os

def create_pdf(text_content, recipient_info, filename="output_letter.pdf", signature_path="temp_signature.png"):
    print("📄 Formatting PDF...")
    
    pdf = FPDF(orientation='P', unit='mm', format='Letter')
    pdf.add_page()
    
    font_path = 'IndieFlower-Regular.ttf'
    
    if os.path.exists(font_path):
        pdf.add_font('IndieFlower', '', font_path)
        has_cursive = True
    else:
        has_cursive = False

    # --- NO HEADER ---
    # We removed the VerbaPost logo here.
    # We just add a small margin to ensure the address isn't stuck to the very top edge.
    pdf.ln(20) 
    
    # ADDRESS
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(0, 6, recipient_info)
    pdf.ln(15)
    
    # BODY
    if has_cursive:
        pdf.set_font('IndieFlower', size=14)
    else:
        pdf.set_font("Helvetica", size=12)
    
    pdf.multi_cell(0, 8, text_content)
    
    # SIGNATURE
    pdf.ln(10)
    if os.path.exists(signature_path):
        try:
            # w=40 keeps it a reasonable size
            pdf.image(signature_path, w=40) 
        except:
            print("Could not load signature image")
    
    # FOOTER
    pdf.set_y(-30)
    pdf.set_font("Helvetica", 'I', 10)
    pdf.cell(0, 10, "Dictated via VerbaPost", ln=1, align='C')
    
    pdf.output(filename)
    return os.path.abspath(filename)