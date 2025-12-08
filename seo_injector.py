import os
import streamlit as st
import shutil

def inject_seo():
    # 1. Locate Streamlit's static directory
    st_dir = os.path.dirname(st.__file__)
    static_dir = os.path.join(st_dir, "static")
    index_path = os.path.join(static_dir, "index.html")
    
    if not os.path.exists(index_path):
        print(f"❌ Error: Could not find index.html at {index_path}")
        return

    print(f"✅ Found Streamlit index at: {index_path}")

    # 2. INJECT SITEMAP & ROBOTS
    for file in ["sitemap.xml", "robots.txt"]:
        if os.path.exists(file):
            dest = os.path.join(static_dir, file)
            shutil.copy(file, dest)
            print(f"✅ Copied {file} to {dest}")
        else:
            print(f"⚠️ Warning: {file} not found in source dir.")

    # 3. DEFINE SEO CONTENT (NoScript)
    # UPDATED: Added new tagline and "Audio Upload" feature to the list.
    seo_html_content = """
    <div id="seo-content" style="display:none;">
        <header>
            <h1>VerbaPost: Send Real Mail from Audio</h1>
            <h2>Making sending physical mail easier.</h2>
            <h3>Texts are trivial. Emails are ignored. REAL MAIL GETS READ.</h3>
        </header>
        <main>
            <h3>Our Mission</h3>
            <p>In a world drowning in digital noise, physical mail has become a superpower. VerbaPost bridges the gap using AI to turn your voice into professional physical letters.</p>
            
            <h3>Key Features</h3>
            <ul>
                <li><strong>Voice Dictation:</strong> Just speak. We type and format it.</li>
                <li><strong>Audio File Upload:</strong> Upload raw .wav, .mp3, or .m4a files for automatic transcription.</li>
                <li><strong>USPS Fulfillment:</strong> Printed, stamped, and mailed in 24 hours.</li>
                <li><strong>Campaign Mode:</strong> Upload CSVs to mail hundreds of constituents instantly.</li>
                <li><strong>Santa Letters:</strong> Magical letters postmarked from the North Pole.</li>
                <li><strong>Heirloom:</strong> Archival quality paper for family memories.</li>
            </ul>
            
            <h3>Services</h3>
            <p><strong>Standard ($2.99):</strong> Everyday correspondence.</p>
            <p><strong>Civic ($6.99):</strong> Write to Congress automatically.</p>
            <p><strong>Campaign ($1.99):</strong> Bulk mailing for activists.</p>
            
            <a href="/?view=login">Login to VerbaPost</a>
            <a href="/?view=legal">Legal & Privacy</a>
        </main>
    </div>
    """

    # 4. READ & REPLACE INDEX.HTML
    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()

    if "<noscript>" in html:
        start = html.find("<noscript>") + len("<noscript>")
        end = html.find("</noscript>")
        new_html = html[:start] + seo_html_content + html[end:]
    else:
        if "id=\"seo-content\"" not in html:
            new_html = html.replace("</body>", f"<noscript>{seo_html_content}</noscript></body>")
        else:
            new_html = html

    # 5. INJECT META TAGS (Social Previews)
    # UPDATED: Added "Making sending physical mail easier" and upload references.
    meta_tags = """
    <title>VerbaPost | Making sending physical mail easier</title>
    <meta property="og:title" content="VerbaPost | Making sending physical mail easier" />
    <meta property="og:description" content="Dictate letters or upload MP3/WAV audio files. We print and mail them for you via USPS." />
    <meta property="og:image" content="https://verbapost.com/static/preview_card.png" />
    <meta name="description" content="Send physical USPS mail from your phone. Voice dictation, audio file upload (wav/mp3), bulk campaigns, and Santa letters." />
    <meta name="keywords" content="voice to mail, upload audio to letter, mp3 to snail mail, wav file to post, send real mail online" />
    """
    
    # Simple check to avoid double injection if running multiple times locally
    if "<meta property=\"og:title\"" not in new_html:
        new_html = new_html.replace("<head>", f"<head>{meta_tags}")
    else:
        # If tags exist but might be old, this simple script skips update to avoid duplication.
        # For a more robust update, we would strip old tags first, but this is usually sufficient for deployment.
        pass

    # 6. SAVE
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(new_html)
    
    print("✅ SEO Injection Complete. index.html updated.")

if __name__ == "__main__":
    inject_seo()