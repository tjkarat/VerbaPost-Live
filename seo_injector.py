import streamlit as st

def inject_meta_tags(mode="archive"):
    """
    Dynamically injects SEO meta tags based on the active mode (Partner vs Archive).
    Uses unsafe_allow_html to embed tags invisibly in the header.
    """
    
    # 1. Define Metadata based on Mode
    if mode == "partner":
        title = "VerbaPost | Client Retention for Estate Planners"
        desc = "Reduce heir attrition. The premier legacy preservation service designed for Estate Planning Attorneys and Wealth Managers."
        image = "https://app.verbapost.com/static/social-preview-b2b.jpg"
    elif mode == "utility":
        title = "VerbaPost | Send Mail Online"
        desc = "Write letters online and we mail them physically. The easiest way to send correspondence."
        image = "https://app.verbapost.com/static/og_image_store.png"
    else:
        # Default: Archive/Heirloom
        title = "VerbaPost | The Family Archive"
        desc = "Preserve your family's legacy. We interview your loved ones over the phone, transcribe their memories, and mail keepsake letters."
        image = "https://app.verbapost.com/static/og_image.png"

    # 2. Construct HTML Block
    meta_html = f"""
    <head>
        <meta property="og:type" content="website">
        <meta property="og:url" content="https://verbapost.com/">
        <meta property="og:title" content="{title}">
        <meta property="og:description" content="{desc}">
        <meta property="og:image" content="{image}">
        
        <meta name="twitter:card" content="summary_large_image">
        <meta name="twitter:title" content="{title}">
        <meta name="twitter:description" content="{desc}">
        <meta name="twitter:image" content="{image}">
    </head>
    """

    # 3. Inject Invisibly
    st.markdown(meta_html, unsafe_allow_html=True)