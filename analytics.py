import streamlit as st
import streamlit.components.v1 as components
import secrets_manager

def inject_ga():
    # 1. Try to find the ID
    ga_id = secrets_manager.get_secret("GA_ID")
    
    # 2. If no ID (like in QA/Streamlit Cloud), STOP.
    if not ga_id:
        print("ℹ️ Analytics: No ID found. Tracking disabled for this environment.")
        return

    # 3. If ID exists (Production), inject it.
    js_breakout = f"""
    <script>
        if (!window.parent.document.getElementById('google-analytics')) {{
            var script = window.parent.document.createElement('script');
            script.src = "https://www.googletagmanager.com/gtag/js?id={ga_id}";
            script.async = true;
            script.id = 'google-analytics';
            window.parent.document.head.appendChild(script);

            script.onload = function() {{
                var script2 = window.parent.document.createElement('script');
                script2.innerHTML = `
                    window.dataLayer = window.dataLayer || [];
                    function gtag(){{dataLayer.push(arguments);}}
                    gtag('js', new Date());
                    gtag('config', '{ga_id}', {{
                        'anonymize_ip': true,
                        'cookie_flags': 'SameSite=None;Secure'
                    }});
                `;
                window.parent.document.head.appendChild(script2);
                console.log("VerbaPost Analytics Active: {ga_id}");
            }};
        }}
    </script>
    """
    components.html(js_breakout, height=0, width=0)