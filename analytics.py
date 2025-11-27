import streamlit as st
import streamlit.components.v1 as components

def inject_ga():
    # YOUR MEASUREMENT ID
    GA_ID = "G-D3P178CESF"
    
    # Define the JS code
    # We use a hidden iframe approach that is more stable in Streamlit
    ga_js = f"""
    <script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
    <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){{dataLayer.push(arguments);}}
        gtag('js', new Date());
        gtag('config', '{GA_ID}', {{
            'anonymize_ip': true
        }});
    </script>
    """
    
    # Inject it into the head of the app invisibly
    # height=0 hides the component visually
    components.html(ga_js, height=0, width=0)