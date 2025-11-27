import streamlit as st

def inject_ga():
    # YOUR MEASUREMENT ID
    GA_ID = "G-D3P178CESF"
    
    # Injected into the <head> logic via streamlit
    # Note: Streamlit executions are wrapped, so we inject this script 
    # to run on load.
    
    ga_code = f"""
    <!-- Global site tag (gtag.js) - Google Analytics -->
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
    # This might print slightly visible whitespace in some themes, but it's the standard way
    st.markdown(ga_code, unsafe_allow_html=True)