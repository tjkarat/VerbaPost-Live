import streamlit as st
import streamlit.components.v1 as components

def inject_ga():
    # YOUR MEASUREMENT ID
    GA_ID = "G-D3P178CESF"
    
    # This script injects the GA tags into the PARENT window (the actual app),
    # breaking out of the Streamlit iframe sandbox.
    js_breakout = f"""
    <script>
        // Check if GA is already loaded to prevent duplicates
        if (!window.parent.document.getElementById('google-analytics')) {{
            // 1. Load the GTag Script
            var script = window.parent.document.createElement('script');
            script.src = "https://www.googletagmanager.com/gtag/js?id={GA_ID}";
            script.async = true;
            script.id = 'google-analytics';
            window.parent.document.head.appendChild(script);

            // 2. Initialize GTag
            script.onload = function() {{
                var script2 = window.parent.document.createElement('script');
                script2.innerHTML = `
                    window.dataLayer = window.dataLayer || [];
                    function gtag(){{dataLayer.push(arguments);}}
                    gtag('js', new Date());
                    gtag('config', '{GA_ID}', {{
                        'anonymize_ip': true,
                        'cookie_flags': 'SameSite=None;Secure'
                    }});
                `;
                window.parent.document.head.appendChild(script2);
                console.log("VerbaPost Analytics Injected Successfully");
            }};
        }}
    </script>
    """
    
    # Inject invisibly
    components.html(js_breakout, height=0, width=0)