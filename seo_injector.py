import os
import streamlit as st

def inject_meta_tags():
    """
    Injects SEO tags and generates sitemap.xml.
    Safe for Read-Only filesystems (will fail silently).
    """
    # --- STATIC FOLDER CONFIG ---
    # Use current working directory for robustness
    static_dir = os.path.join(os.getcwd(), "static")
    
    if not os.path.exists(static_dir):
        try:
            os.makedirs(static_dir)
        except OSError:
            pass # Fail silently

    # --- SITEMAP GENERATION ---
    sitemap_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
   <url><loc>https://www.verbapost.com/</loc><priority>1.0</priority></url>
</urlset>"""

    try:
        with open(os.path.join(static_dir, "sitemap.xml"), "w") as f:
            f.write(sitemap_content)
    except Exception:
        pass 

    # --- INJECT HTML TAGS ---
    try:
        # Target the streamlit static index.html
        st_dir = os.path.dirname(st.__file__)
        index_path = os.path.join(st_dir, "static", "index.html")
        
        if os.path.exists(index_path):
            with open(index_path, "r", encoding="utf-8") as f:
                html = f.read()

            meta_tags = """
            <title>VerbaPost | Making sending physical mail easier</title>
            <meta name="description" content="Send physical USPS mail from your phone." />
            """
            
            # Simple check to avoid duplicate injection
            if "VerbaPost | Making sending" not in html:
                html = html.replace("<head>", f"<head>{meta_tags}")
                try:
                    with open(index_path, "w", encoding="utf-8") as f:
                        f.write(html)
                except PermissionError:
                    pass # Expected in some cloud envs
                
    except Exception:
        pass # SEO is non-critical

if __name__ == "__main__":
    inject_meta_tags()