import streamlit as st
import streamlit.components.v1 as components

def listen_for_oauth():
    """
    Injects JS to detect Supabase OAuth tokens in the TOP URL hash 
    and reloads the page with them as query parameters.
    """
    # If we already have the token in query params, stop listening to avoid loops
    if "access_token" in st.query_params:
        return

    # JS Code: AGGRESSIVE REDIRECT
    # We use window.top to break out of the Streamlit iframe sandbox
    js_code = """
    <script>
    (function() {
        console.log("VerbaPost Auth Listener: Active");
        try {
            // Check the TOP window (the browser address bar)
            const hash = window.top.location.hash.substring(1);
            
            if (hash) {
                console.log("Hash detected, processing...");
                const params = new URLSearchParams(hash);
                const access_token = params.get('access_token');
                const refresh_token = params.get('refresh_token');
                
                if (access_token) {
                    console.log("Token found. Redirecting...");
                    
                    // Construct new URL with query params
                    const currentUrl = new URL(window.top.location.href);
                    currentUrl.searchParams.set('access_token', access_token);
                    currentUrl.searchParams.set('refresh_token', refresh_token);
                    currentUrl.searchParams.set('type', 'oauth_callback');
                    currentUrl.hash = ''; // Clear the hash
                    
                    // Force reload
                    window.top.location.href = currentUrl.toString();
                }
            }
        } catch (e) {
            console.error("OAuth Listener Error:", e);
            // Fallback: If we can't access window.top due to strict cross-origin rules,
            // we display a message in the console.
        }
    })();
    </script>
    """
    
    # Render invisible component to execute JS
    components.html(js_code, height=0, width=0)