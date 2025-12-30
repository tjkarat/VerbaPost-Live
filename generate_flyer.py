import qrcode
from fpdf import FPDF
import os

# --- CONFIGURATION ---
OUTPUT_FILENAME = "VerbaPost_Flyer.pdf"
URL_TO_ENCODE = "https://verbapost.com"
BRAND_RED = (217, 48, 37)  # #d93025
BG_CREAM = (253, 251, 247) # #fdfbf7

class FlyerPDF(FPDF):
    def header(self):
        # No standard header for a flyer
        pass

    def footer(self):
        # Simple footer
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, "VerbaPost - The Family Archive Service", align="C")

def create_flyer():
    pdf = FlyerPDF(orientation='P', unit='mm', format='Letter')
    pdf.add_page()
    
    # 1. Background Color (Cream)
    pdf.set_fill_color(*BG_CREAM)
    pdf.rect(0, 0, 215.9, 279.4, 'F')

    # 2. Main Headline
    pdf.set_y(30)
    pdf.set_font("Times", "B", 36)
    pdf.set_text_color(20, 20, 20)
    pdf.multi_cell(0, 12, "Don't Let Their\nStories Fade.", align="C")

    # 3. Subheadline
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(80, 80, 80)
    pdf.ln(5)
    pdf.multi_cell(0, 8, "Capture your parents' memories forever\nwith just a simple phone call.", align="C")

    # 4. Divider Line
    pdf.ln(10)
    pdf.set_draw_color(*BRAND_RED)
    pdf.set_line_width(0.5)
    # Draw line centered (approx 100mm wide)
    x_start = (215.9 - 100) / 2
    pdf.line(x_start, pdf.get_y(), x_start + 100, pdf.get_y())
    pdf.ln(15)

    # 5. Problem / Solution Section
    pdf.set_left_margin(25)
    pdf.set_right_margin(25)
    
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*BRAND_RED)
    pdf.cell(0, 8, "THE PROBLEM:", ln=True)
    
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(50, 50, 50)
    pdf.multi_cell(0, 6, "You want to capture your loved one's life stories, but writing them down is hard, and they struggle with apps like Zoom.")
    pdf.ln(5)

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*BRAND_RED)
    pdf.cell(0, 8, "THE SOLUTION:", ln=True)
    
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(50, 50, 50)
    pdf.multi_cell(0, 6, "VerbaPost is a secure 'Voice Biographer.' We turn their spoken memories into a physical family archive without them ever touching a computer.")
    pdf.ln(15)

    # 6. Three Steps (Using Text instead of Emojis for PDF compatibility)
    pdf.set_font("Times", "B", 14)
    pdf.set_text_color(0, 0, 0)
    
    steps = [
        ("1. WE CALL THEM", "We ring their regular telephone number. No apps, no WiFi, and no smartphones required."),
        ("2. THEY SHARE", "Our friendly voice interviewer asks questions like 'How did you meet Mom?'"),
        ("3. YOU KEEP IT", "We transcribe their voice and mail you a beautiful, physical keepsake letter.")
    ]

    for title, desc in steps:
        pdf.set_font("Times", "B", 13)
        pdf.cell(0, 6, title, ln=True)
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 6, desc)
        pdf.ln(4)

    # 7. QR Code Generation
    qr = qrcode.QRCode(box_size=10, border=1)
    qr.add_data(URL_TO_ENCODE)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save("temp_qr.png")

    # 8. Bottom CTA Section
    pdf.set_y(-85) # Move to bottom
    
    # Left side text
    pdf.set_font("Times", "B", 18)
    pdf.set_text_color(*BRAND_RED)
    pdf.text(25, 210, "Start Your Archive Today")
    
    pdf.set_font("Helvetica", "I", 12)
    pdf.set_text_color(50, 50, 50)
    pdf.text(25, 218, "Preserve their voice. Own their legacy.")
    
    pdf.set_font("Helvetica", "", 10)
    pdf.text(25, 228, "Scan to visit VerbaPost.com ->")

    # Right side QR Code
    pdf.image("temp_qr.png", x=130, y=195, w=50)

    # Cleanup
    if os.path.exists("temp_qr.png"):
        os.remove("temp_qr.png")

    # Output
    pdf.output(OUTPUT_FILENAME)
    print(f"✅ Success! Created {OUTPUT_FILENAME}")

if __name__ == "__main__":
    create_flyer()
