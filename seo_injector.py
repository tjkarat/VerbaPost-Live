import streamlit as st

def inject_meta():
    """
    Injects SEO metadata.
    NOTE: In Streamlit, <title> is best handled by st.set_page_config() in main.py.
    This function handles Description, Keywords, and Open Graph (Social Sharing).
    """
    meta_tags = """
    <meta name="description" content="VerbaPost: The easiest way to preserve family stories. We interview your loved ones over the phone and mail you physical legacy letters. 100% Private & Secure.">
    <meta name="keywords" content="family archive, voice biographer, record parents stories, legacy letters, end of life planning, death dossier, audio keepsake, oral history service, VerbaPost">
    <meta name="author" content="VerbaPost">
    
    <meta property="og:type" content="website">
    <meta property="og:url" content="https://verbapost.com/">
    <meta property="og:title" content="VerbaPost | Real Mail Gets Read">
    <meta property="og:description" content="Don't let their stories fade. Our automated phone interviewer captures your family's memories and turns them into physical keepsake letters.">
    <meta property="og:image" content="https://verbapost.com/app/static/social_preview.png">

    <meta property="twitter:card" content="summary_large_image">
    <meta property="twitter:url" content="https://verbapost.com/">
    <meta property="twitter:title" content="VerbaPost | Real Mail Gets Read">
    <meta property="twitter:description" content="No apps. No login. Just a phone call. We record and transcribe your family's history for you.">
    <meta property="twitter:image" content="https://verbapost.com/app/static/social_preview.png">
    """
    
    # Inject into the app
    st.markdown(meta_tags, unsafe_allow_html=True)