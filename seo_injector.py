import streamlit as st

def inject_meta():
    """
    Injects high-value SEO tags for End of Life & Legacy services.
    Call this function at the top of main.py.
    """
    meta_tags = """
    <title>VerbaPost | Secure End of Life & Legacy Letters</title>
    <meta name="title" content="VerbaPost | Secure End of Life & Legacy Letters">
    <meta name="description" content="The secure way to document and mail final wishes, wills, and legacy letters. Printed on archival paper and delivered via USPS Certified Mail. 100% Private.">
    <meta name="keywords" content="end of life letter, legacy planning, death dossier, ethical will, write my final wishes, send certified mail online, posthumous letters, VerbaPost">
    
    <meta property="og:type" content="website">
    <meta property="og:url" content="https://verbapost.com/">
    <meta property="og:title" content="VerbaPost | Leave a Lasting Legacy">
    <meta property="og:description" content="Don't leave things unsaid. Securely write, print, and certify your final letters and wishes today.">
    <meta property="og:image" content="https://verbapost.com/static/social_preview.png">

    <meta property="twitter:card" content="summary_large_image">
    <meta property="twitter:url" content="https://verbapost.com/">
    <meta property="twitter:title" content="VerbaPost | Secure Legacy Letters">
    <meta property="twitter:description" content="The secure platform for end-of-life correspondence. Archival quality. Certified delivery.">
    
    <meta name="geo.region" content="US">
    <meta name="geo.position" content="37.0902;-95.7129">
    <meta name="ICBM" content="37.0902, -95.7129">
    """
    
    # Inject into the <head> of the Streamlit app
    st.markdown(meta_tags, unsafe_allow_html=True)