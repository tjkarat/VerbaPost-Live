import streamlit as st

def listen_for_oauth():
    """
    Injects JS to detect Supabase OAuth tokens in the URL hash 
    and reloads the page with them as query parameters so Python can read them.
    """
    # If we already have the token in query params, stop listening
    if "access_token" in st.query_params:
        return

    # JS Code: If hash exists, move it to query params and reload
    js_code = """
    <script>
    const hash = window.location.hash.substring(1);
    if (hash) {
        const params = new URLSearchParams(hash);
        const access_token = params.get('access_token');
        const refresh_token = params.get('refresh_token');
        
        if (access_token) {
            // Rewrite URL to include params so Streamlit sees them
            const newUrl = window.location.origin + window.location.pathname + 
                           '?access_token=' + access_token + 
                           '&refresh_token=' + refresh_token + 
                           '&type=oauth_callback';
            window.location.href = newUrl;
        }
    }
    </script>
    """
    st.components.v1.html(js_code, height=0, width=0)
