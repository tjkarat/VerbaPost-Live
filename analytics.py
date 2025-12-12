import streamlit as st
import streamlit.components.v1 as components
import secrets_manager
import logging
import json
from datetime import datetime

# Configure Logging for Server-Side Tracking
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Analytics")

def inject_ga():
    """
    Injects Google Analytics 4 (GA4) into the Streamlit app.
    Retained from original file.
    """
    # 1. Get Dynamic ID
    ga_id = secrets_manager.get_secret("GA_ID")
    
    # 2. Safety Check
    if not ga_id:
        # Silently fail or log debug info if no ID is found
        return

    # 3. JS Injection (Double Curly Braces for JS, Single for Python variables)
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

def track_event(user_email, event_name, properties=None):
    """
    Logs critical user actions to the console (Cloud Logging).
    This is the NEW function for Phase 3.
    
    Args:
        user_email (str): Who did it?
        event_name (str): What did they do? (e.g., 'payment_success')
        properties (dict): Details (e.g., {'amount': 2.99})
    """
    if properties is None: properties = {}
    
    timestamp = datetime.utcnow().isoformat()
    
    # 1. Structured Log (JSON format is best for Cloud logging tools)
    log_payload = {
        "timestamp": timestamp,
        "user": user_email,
        "event": event_name,
        "properties": properties
    }
    
    # Log to server console
    logger.info(f"📊 EVENT: {json.dumps(log_payload)}")
    
    # 2. Session Debugging (Optional: helps you see it in the UI session state if needed)
    if "session_events" not in st.session_state:
        st.session_state.session_events = []
    st.session_state.session_events.append(log_payload)