import streamlit as st

def listen_for_oauth():
    """
    Injects JS to detect Supabase OAuth tokens in the PARENT URL hash 
    and reloads the page with them as query parameters.
    """
    # If we already have the token in query params, stop listening
    if "access_token" in st.query_params:
        return

    # JS Code: ACCESS PARENT WINDOW
    js_code = """
    <script>
    try {
        // Use window.parent to escape the Streamlit iframe sandbox
        const hash = window.parent.location.hash.substring(1);
        
        if (hash) {
            const params = new URLSearchParams(hash);
            const access_token = params.get('access_token');
            const refresh_token = params.get('refresh_token');
            
            if (access_token) {
                // Construct new URL with query params instead of hash
                const currentUrl = new URL(window.parent.location.href);
                currentUrl.searchParams.set('access_token', access_token);
                currentUrl.searchParams.set('refresh_token', refresh_token);
                currentUrl.searchParams.set('type', 'oauth_callback');
                currentUrl.hash = ''; // Clear the hash
                
                // Force reload to the new URL
                window.parent.location.href = currentUrl.toString();
            }
        }
    } catch (e) {
        console.error("OAuth Listener Error:", e);
    }
    </script>
    """
    st.components.v1.html(js_code, height=0, width=0)