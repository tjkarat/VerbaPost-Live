import streamlit as st

def inject_meta():
    """
    Injects high-value SEO tags.
    Updated for v3.4 to emphasize Family Archive (Heirloom) & Legacy features.
    """
    meta_tags = """
    <title>VerbaPost | The Family Archive & Legacy Letters</title>
    <meta name="title" content="VerbaPost | The Family Archive & Legacy Letters">
    <meta name="description" content="Securely preserve family stories and final wishes. The easiest way to record parents' memories via phone and mail physical legacy letters. 100% Private & Archival.">
    <meta name="keywords" content="family archive, voice biography, record parents stories, phone interview service, legacy letters, end of life planning, death dossier, write my final wishes, send certified mail online, VerbaPost">
    
    <meta property="og:type" content="website">
    <meta property="og:url" content="https://verbapost.com/">
    <meta property="og:title" content="VerbaPost | Capture the Story Before It's Gone">
    <meta property="og:description" content="Don't let family stories fade. Use our Automated Phone Biographer to capture memories and print them as keepsake letters.">
    <meta property="og:image" content="https://verbapost.com/static/social_preview_heirloom.png">

    <meta property="twitter:card" content="summary_large_image">
    <meta property="twitter:url" content="https://verbapost.com/">
    <meta property="twitter:title" content="VerbaPost | Family Archive & Legacy">
    <meta property="twitter:description" content="The secure platform for family history and end-of-life correspondence. Voice-to-Mail technology.">
    
    <meta name="geo.region" content="US">
    <meta name="geo.position" content="37.0902;-95.7129">
    <meta name="ICBM" content="37.0902, -95.7129">
    """
    
    # Inject into the <head> of the Streamlit app
    st.markdown(meta_tags, unsafe_allow_html=True)