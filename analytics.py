import streamlit as st
import streamlit.components.v1 as components
import secrets_manager # <--- Import your secrets manager

def inject_ga():
    # --- 1. GET DYNAMIC ID ---
    # Instead of hardcoding, we ask the environment for the ID.
    # On GCP, this looks at your Environment Variables.
    # On Streamlit Cloud, this looks at your Secrets.
    ga_id = secrets_manager.get_secret("GA_ID")
    
    # Safety Check: If we forgot to set the ID, don't crash, just skip.
    if not ga_id:
        print("⚠️ Analytics: No GA_ID found in secrets. Skipping injection.")
        return

    # --- 2. YOUR WORKING LOGIC (Preserved) ---
    # I have not touched the JS logic below, only replaced the hardcoded string with {ga_id}
    js_breakout = f"""
    <script>
        // Check if GA is already loaded to prevent duplicates
        if (!window.parent.document.getElementById('google-analytics')) {{
            // 1. Load the GTag Script
            var script = window.parent.document.createElement('script');
            script.src = "https://www.googletagmanager.com/gtag/js?id={ga_id}";
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
                    gtag('config', '{ga_id}', {{
                        'anonymize_ip': true,
                        'cookie_flags': 'SameSite=None;Secure'
                    }});
                `;
                window.parent.document.head.appendChild(script2);
                console.log("VerbaPost Analytics Injected Successfully: {ga_id}");
            }};
        }}
    </script>
    """
    
    # Inject invisibly
    components.html(js_breakout, height=0, width=0)