import os
import streamlit as st

# RENAMED from inject_seo to inject_meta_tags to match main.py
def inject_meta_tags():
    # --- 1. SETUP STATIC PATHS ---
    # Use the static folder in your current project
    static_dir = os.path.join(os.getcwd(), "static")
    
    # Ensure project static folder exists
    if not os.path.exists(static_dir):
        try:
            os.makedirs(static_dir)
            print(f"✅ Created local static directory at {static_dir}")
        except OSError as e:
            # Silent fail if filesystem is read-only
            print(f"❌ Could not create static folder: {e}")
            return

    # --- 2. GENERATE SITEMAP.XML ---
    sitemap_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
   <url>
      <loc>https://www.verbapost.com/</loc>
      <lastmod>2025-12-08</lastmod>
      <changefreq>daily</changefreq>
      <priority>1.0</priority>
   </url>
   <url>
      <loc>https://www.verbapost.com/?view=login</loc>
      <changefreq>monthly</changefreq>
      <priority>0.8</priority>
   </url>
   <url>
      <loc>https://www.verbapost.com/?view=legacy</loc>
      <changefreq>yearly</changefreq>
      <priority>0.9</priority>
   </url>
   <url>
      <loc>https://www.verbapost.com/?view=legal</loc>
      <changefreq>yearly</changefreq>
      <priority>0.5</priority>
   </url>
</urlset>"""

    try:
        with open(os.path.join(static_dir, "sitemap.xml"), "w") as f:
            f.write(sitemap_content)
        # print(f"✅ Created sitemap.xml") 
    except Exception as e:
        print(f"⚠️ Sitemap creation failed (Permission): {e}")

    # --- 3. GENERATE ROBOTS.TXT ---
    robots_content = """User-agent: *
Allow: /

Sitemap: https://www.verbapost.com/static/sitemap.xml
"""
    try:
        with open(os.path.join(static_dir, "robots.txt"), "w") as f:
            f.write(robots_content)
        # print(f"✅ Created robots.txt")
    except Exception as e:
        print(f"⚠️ Robots.txt creation failed: {e}")

    # --- 4. INJECT HTML TAGS (Header & Body) ---
    # We attempt to find the Streamlit library's index.html to inject tags directly.
    # This is wrapped in try/except because Cloud environments are often Read-Only.
    try:
        st_dir = os.path.dirname(st.__file__)
        index_path = os.path.join(st_dir, "static", "index.html")
        
        if os.path.exists(index_path):
            # Read current HTML
            with open(index_path, "r", encoding="utf-8") as f:
                html = f.read()

            # A. Inject SEO Content (Body)
            # This helps crawlers see text content even if the JS app loads slowly
            seo_html_content = """
            <div id="seo-content" style="display:none;">
                <header>
                    <h1>VerbaPost: Send Real Mail from Audio</h1>
                    <h2>Making sending physical mail easier.</h2>
                </header>
                <main>
                    <h3>Mission</h3>
                    <p>VerbaPost bridges the gap using AI to turn your voice into professional physical letters.</p>
                    <p>Services: Voice-to-Mail, Legacy Letters, Bulk Campaigns.</p>
                </main>
            </div>
            """
            
            # Only inject if not already present
            if "id=\"seo-content\"" not in html:
                if "<noscript>" in html:
                    start = html.find("<noscript>") + len("<noscript>")
                    end = html.find("</noscript>")
                    html = html[:start] + seo_html_content + html[end:]
                else:
                    html = html.replace("</body>", f"<noscript>{seo_html_content}</noscript></body>")

            # B. Inject Meta Tags & Sitemap Link (Head)
            meta_tags = """
            <meta name="description" content="Send physical USPS mail from your phone. Voice dictation, audio file upload (wav/mp3), and bulk campaigns." />
            <meta property="og:title" content="VerbaPost | Send Real Letters" />
            <meta property="og:description" content="Dictate letters or upload MP3/WAV audio files. We print and mail them for you via USPS." />
            <meta property="og:image" content="https://verbapost.com/static/preview_card.png" />
            <link rel="sitemap" type="application/xml" title="Sitemap" href="./static/sitemap.xml" />
            """
            
            if "<meta property=\"og:title\"" not in html:
                html = html.replace("<head>", f"<head>{meta_tags}")
            
            # ATTEMPT WRITE
            # If filesystem is read-only (Cloud Run), this throws PermissionError
            try:
                with open(index_path, "w", encoding="utf-8") as f:
                    f.write(html)
                print("✅ SEO Injection Complete: Meta tags added to core index.html.")
            except PermissionError:
                # Expected behavior in Cloud Run - just log and continue
                print("⚠️ Could not inject Meta Tags into index.html (Read-Only Filesystem). Skipping.")
                
    except Exception as e:
        print(f"⚠️ SEO Injection skipped: {e}")

if __name__ == "__main__":
    inject_meta_tags()