import os
import streamlit as st

def inject_seo():
    # 1. Locate Streamlit's static directory
    st_dir = os.path.dirname(st.__file__)
    static_dir = os.path.join(st_dir, "static")
    index_path = os.path.join(static_dir, "index.html")
    
    if not os.path.exists(static_dir):
        print(f"❌ Error: Streamlit static folder not found at {static_dir}")
        return

    # --- 2. GENERATE SITEMAP.XML ---
    # This creates the physical file
    sitemap_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
   <url>
      <loc>https://www.verbapost.com/</loc>
      <lastmod>2025-12-07</lastmod>
      <changefreq>daily</changefreq>
      <priority>1.0</priority>
   </url>
   <url>
      <loc>https://www.verbapost.com/?view=login</loc>
      <changefreq>monthly</changefreq>
      <priority>0.8</priority>
   </url>
   <url>
      <loc>https://www.verbapost.com/?view=legal</loc>
      <changefreq>yearly</changefreq>
      <priority>0.5</priority>
   </url>
</urlset>"""

    sitemap_path = os.path.join(static_dir, "sitemap.xml")
    with open(sitemap_path, "w") as f:
        f.write(sitemap_content)
    print(f"✅ Created sitemap.xml at {sitemap_path}")

    # --- 3. GENERATE ROBOTS.TXT ---
    # This tells Google where to find the sitemap
    robots_content = """User-agent: *
Allow: /

Sitemap: https://www.verbapost.com/static/sitemap.xml
"""
    robots_path = os.path.join(static_dir, "robots.txt")
    with open(robots_path, "w") as f:
        f.write(robots_content)
    print(f"✅ Created robots.txt at {robots_path}")

    # --- 4. INJECT HTML TAGS ---
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            html = f.read()

        # A. Inject SEO Content (Body)
        seo_html_content = """
        <div id="seo-content" style="display:none;">
            <header>
                <h1>VerbaPost: Send Real Mail from Audio</h1>
                <h2>Making sending physical mail easier.</h2>
            </header>
            <main>
                <h3>Mission</h3>
                <p>VerbaPost bridges the gap using AI to turn your voice into professional physical letters.</p>
                <ul>
                    <li><strong>Voice Dictation:</strong> Just speak. We type and format it.</li>
                    <li><strong>Audio File Upload:</strong> Upload raw .wav, .mp3, or .m4a files.</li>
                    <li><strong>USPS Fulfillment:</strong> Printed, stamped, and mailed in 24 hours.</li>
                </ul>
            </main>
        </div>
        """
        
        if "id=\"seo-content\"" not in html:
            if "<noscript>" in html:
                start = html.find("<noscript>") + len("<noscript>")
                end = html.find("</noscript>")
                html = html[:start] + seo_html_content + html[end:]
            else:
                html = html.replace("</body>", f"<noscript>{seo_html_content}</noscript></body>")

        # B. Inject Meta Tags & Sitemap Link (Head)
        meta_tags = """
        <title>VerbaPost | Making sending physical mail easier</title>
        <meta name="description" content="Send physical USPS mail from your phone. Voice dictation, audio file upload (wav/mp3), and bulk campaigns." />
        <meta property="og:title" content="VerbaPost | Making sending physical mail easier" />
        <meta property="og:description" content="Dictate letters or upload MP3/WAV audio files. We print and mail them for you via USPS." />
        <meta property="og:image" content="https://verbapost.com/static/preview_card.png" />
        <link rel="sitemap" type="application/xml" title="Sitemap" href="./static/sitemap.xml" />
        """
        
        if "<meta property=\"og:title\"" not in html:
            html = html.replace("<head>", f"<head>{meta_tags}")
        
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(html)
        print("✅ SEO Injection Complete: Meta tags & Sitemap link added.")

if __name__ == "__main__":
    inject_seo()