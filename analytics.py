import streamlit as st

def inject_ga():
    # YOUR MEASUREMENT ID
    GA_ID = "G-D3P178CESF"
    
    # Note: We use 'unsafe_allow_html' to inject the script tag directly into the page body.
    # This works better than components.html for tracking main page views.
    
    ga_code = f"""
    <script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
    <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){{dataLayer.push(arguments);}}
        gtag('js', new Date());
        gtag('config', '{GA_ID}', {{
            'anonymize_ip': true,
            'cookie_flags': 'SameSite=None;Secure'
        }});
    </script>
    """
    st.markdown(ga_code, unsafe_allow_html=True)