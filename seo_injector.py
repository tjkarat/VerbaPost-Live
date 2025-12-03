import os
import streamlit as st

def inject_seo():
    # 1. Locate Streamlit's static index.html
    # Streamlit installs into site-packages, so we find it relative to the module
    st_dir = os.path.dirname(st.__file__)
    index_path = os.path.join(st_dir, "static", "index.html")
    
    if not os.path.exists(index_path):
        print(f"❌ Error: Could not find index.html at {index_path}")
        return

    print(f"✅ Found Streamlit index at: {index_path}")

    # 2. Define the "No-Script" Content (What Google Sees)
    # This mimics your Splash Page text so crawlers can read it.
    seo_html_content = """
    <div id="seo-content" style="padding: 20px; font-family: sans-serif; color: #333;">
        <header>
            <h1>VerbaPost: Send Real Mail from Audio</h1>
            <h2>Texts are trivial. Emails are ignored. REAL MAIL GETS READ.</h2>
        </header>
        <main>
            <h3>Our Mission</h3>
            <p>In a world drowning in digital noise, physical mail has become a superpower. VerbaPost bridges the gap using AI to turn your voice into professional physical letters.</p>
            
            <h3>Key Features</h3>
            <ul>
                <li><strong>Voice Dictation:</strong> Just speak. We type and format it.</li>
                <li><strong>USPS Fulfillment:</strong> Printed, stamped, and mailed in 24 hours.</li>
                <li><strong>Campaign Mode:</strong> Upload CSVs to mail hundreds of constituents instantly.</li>
                <li><strong>Santa Letters:</strong> Magical letters postmarked from the North Pole.</li>
                <li><strong>Heirloom:</strong> Archival quality paper for family memories.</li>
            </ul>
            
            <h3>Services</h3>
            <p><strong>Standard ($2.99):</strong> Everyday correspondence.</p>
            <p><strong>Civic ($6.99):</strong> Write to Congress automatically.</p>
            <p><strong>Campaign ($1.99):</strong> Bulk mailing for activists.</p>
            
            <a href="/login">Login to VerbaPost</a>
        </main>
    </div>
    """

    # 3. Read & Replace
    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Replace the default "You need to enable JavaScript" warning
    # with our rich SEO content.
    if "<noscript>" in html:
        # Replace content inside noscript
        start = html.find("<noscript>") + len("<noscript>")
        end = html.find("</noscript>")
        new_html = html[:start] + seo_html_content + html[end:]
    else:
        # Fallback: Insert at end of body if noscript is missing (rare)
        new_html = html.replace("</body>", f"<noscript>{seo_html_content}</noscript></body>")

    # 4. Inject Meta Tags (Social Previews)
    # This ensures links look good on iMessage/Twitter
    meta_tags = """
    <meta property="og:title" content="VerbaPost: The Voice-to-Mail Platform" />
    <meta property="og:description" content="Dictate letters to Congress, Santa, or family. We print and mail them for you." />
    <meta property="og:image" content="https://verbapost.com/static/preview_card.png" />
    <meta name="description" content="Send physical USPS mail from your phone. Voice dictation, bulk campaigns, and Santa letters." />
    """
    new_html = new_html.replace("<head>", f"<head>{meta_tags}")

    # 5. Save
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(new_html)
    
    print("✅ SEO Injection Complete. index.html updated.")

if __name__ == "__main__":
    inject_seo()
