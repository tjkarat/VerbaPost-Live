import os
import streamlit as st

def inject_seo():
    # --- FIX: USE PROJECT FOLDER, NOT LIBRARY FOLDER ---
    # Old/Bad: static_dir = os.path.join(os.path.dirname(st.__file__), "static")
    # New/Good: Use the static folder in your current project
    static_dir = os.path.join(os.getcwd(), "static")
    
    # Ensure project static folder exists
    if not os.path.exists(static_dir):
        try:
            os.makedirs(static_dir)
            print(f"✅ Created local static directory at {static_dir}")
        except OSError as e:
            print(f"❌ Could not create static folder: {e}")
            return

    # --- GENERATE SITEMAP.XML ---
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
      <loc>https://www.verbapost.com/?view=legal</loc>
      <changefreq>yearly</changefreq>
      <priority>0.5</priority>
   </url>
</urlset>"""

    try:
        with open(os.path.join(static_dir, "sitemap.xml"), "w") as f:
            f.write(sitemap_content)
        print(f"✅ Created sitemap.xml at {static_dir}/sitemap.xml")
    except Exception as e:
        print(f"⚠️ Sitemap creation failed (Permission): {e}")

    # --- GENERATE ROBOTS.TXT ---
    robots_content = """User-agent: *
Allow: /

Sitemap: https://www.verbapost.com/app/static/sitemap.xml
"""
    try:
        with open(os.path.join(static_dir, "robots.txt"), "w") as f:
            f.write(robots_content)
        print(f"✅ Created robots.txt at {static_dir}/robots.txt")
    except Exception as e:
        print(f"⚠️ Robots.txt creation failed: {e}")

    # --- INJECT HTML TAGS ---
    # We still need to find index.html to inject meta tags.
    # This part MUST access the library path, but we only READ/WRITE it if we have permission.
    # In many cloud envs, index.html is read-only. We wrap this in try/except to prevent crashing.
    try:
        st_dir = os.path.dirname(st.__file__)
        index_path = os.path.join(st_dir, "static", "index.html")
        
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
            
            # ATTEMPT WRITE
            try:
                with open(index_path, "w", encoding="utf-8") as f:
                    f.write(html)
                print("✅ SEO Injection Complete: Meta tags added to core index.html.")
            except PermissionError:
                print("⚠️ Could not inject Meta Tags into index.html (Read-Only Filesystem). Skipping.")
                
    except Exception as e:
        print(f"⚠️ SEO Injection skipped: {e}")

if __name__ == "__main__":
    inject_seo()