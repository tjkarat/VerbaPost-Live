import os

def create_static_assets():
    # 1. Ensure static directory exists
    if not os.path.exists("static"):
        os.makedirs("static")
        print("✅ Created 'static' directory.")

    # 2. Create sitemap.xml
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
    
    with open("static/sitemap.xml", "w") as f:
        f.write(sitemap_content)
    print("✅ Created static/sitemap.xml")

    # 3. Create robots.txt
    robots_content = """User-agent: *
Allow: /

Sitemap: https://www.verbapost.com/app/static/sitemap.xml
"""
    with open("static/robots.txt", "w") as f:
        f.write(robots_content)
    print("✅ Created static/robots.txt")

if __name__ == "__main__":
    create_static_assets()
