import streamlit.components.v1 as components

import streamlit.components.v1 as components
import streamlit as st

def inject_ga():
    # REPLACE 'G-XXXXXXXXXX' with your actual Measurement ID
    measurement_id = 'G-D3P178CESF' 
    
    # Option 1: Component Injection (Standard)
    ga_js = f"""
    <!-- Google tag (gtag.js) -->
    <script async src="https://www.googletagmanager.com/gtag/js?id={measurement_id}"></script>
    <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){{dataLayer.push(arguments);}}
        gtag('js', new Date());
        gtag('config', '{measurement_id}', {{
            'cookie_flags': 'SameSite=None;Secure'
        }});
        console.log('GA4 Loaded: {measurement_id}');
    </script>
    """
    components.html(ga_js, height=0, width=0)