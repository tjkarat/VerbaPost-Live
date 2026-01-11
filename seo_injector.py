import streamlit as st

def inject_meta_tags(mode="archive"):
    """
    Injects HTML Meta Tags for SEO and Social Sharing.
    Streamlit does not allow direct editing of index.html, so we inject
    these into the <head> via the markdown unsafe_allow_html hack.
    """
    
    # --- LOGIC RESTORED FROM MAIN.PY ---
    if mode == "partner":
        title = "VerbaPost | Estate Planning Client Retention"
        description = "FINRA-compliant ($99) client gifts. Reduce heir attrition with high-end legacy letters."
        keywords = "client retention, estate planning gifts, legal client appreciation, legacy letters"
    elif mode == "archive":
        title = "VerbaPost | The Family Archive"
        description = "Preserve your family's legacy. We interview your loved ones over the phone and mail you physical keepsake letters."
        keywords = "family history, voice biography, letter service, genealogy, oral history"
    else:
        title = "VerbaPost | Send Mail Online"
        description = "The easiest way to send physical letters from your screen. No stamps, no printers. Just write and send."
        keywords = "mail letters online, snail mail, post office, write letters, pdf to mail"

    # Define the HTML block
    meta_html = f"""
    <head>
        <title>{title}</title>
        <meta name="title" content="{title}">
        <meta name="description" content="{description}">
        <meta name="keywords" content="{keywords}">

        <meta property="og:type" content="website">
        <meta property="og:url" content="https://verbapost.com/">
        <meta property="og:title" content="{title}">
        <meta property="og:description" content="{description}">
        <meta property="og:image" content="https://verbapost.com/static/og_image.png">

        <meta property="twitter:card" content="summary_large_image">
        <meta property="twitter:url" content="https://verbapost.com/">
        <meta property="twitter:title" content="{title}">
        <meta property="twitter:description" content="{description}">
        <meta property="twitter:image" content="https://verbapost.com/static/og_image.png">
        
        <meta name="google-site-verification" content="YOUR_GOOGLE_VERIFICATION_CODE_HERE" />
    </head>
    """
    
    # Inject styles to hide the default Streamlit footer/hamburger if desired
    hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    </style>
    """

    st.markdown(meta_html, unsafe_allow_html=True)
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Helper alias
inject_seo = inject_meta_tags