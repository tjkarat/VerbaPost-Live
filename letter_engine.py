from fpdf import FPDF
import os
import tempfile

class HeirloomLetter(FPDF):
    def __init__(self):
        # FIX: Explicitly set format to 'Letter' (8.5x11) for US Mail compatibility
        super().__init__(orientation='P', unit='mm', format='Letter')

    def header(self):
        # Optional: Add a subtle logo or "The Family Archive" at the top
        self.set_font('Courier', 'B', 12)
        self.cell(0, 10, 'The Family Archive', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        # Page numbers
        self.set_y(-15)
        self.set_font('Courier', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def create_pdf(text_content, recipient_name, date_str):
    """
    Generates a US LETTER sized PDF file.
    """
    # Initialize with the new class that forces 'Letter' size
    pdf = HeirloomLetter()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # 1. Date & Salutation
    pdf.set_font("Courier", "", 12)
    pdf.cell(0, 10, f"Date: {date_str}", ln=True)
    pdf.ln(5)
    pdf.cell(0, 10, f"Dear {recipient_name},", ln=True)
    pdf.ln(10)
    
    # 2. The Story Body
    # Convert standard text to latin-1 to avoid encoding errors
    try:
        safe_text = text_content.encode('latin-1', 'replace').decode('latin-1')
    except:
        safe_text = text_content
        
    pdf.multi_cell(0, 6, safe_text)
    
    # 3. Sign-off
    pdf.ln(10)
    pdf.cell(0, 10, "With love,", ln=True)
    pdf.cell(0, 10, "Mom", ln=True)
    
    # 4. Save to Temp File
    temp_dir = tempfile.gettempdir()
    safe_date = date_str.replace(' ', '_').replace(',', '')
    file_name = f"Letter_{safe_date}.pdf"
    file_path = os.path.join(temp_dir, file_name)
    
    pdf.output(file_path)
    return file_path