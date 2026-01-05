import streamlit as st
import streamlit.components.v1 as components

def listen_for_oauth():
    """
    Injects JS to detect Supabase OAuth tokens in the URL hash 
    and reloads the page with them as query parameters.
    """
    # If we already have the token in query params, stop listening
    if "access_token" in st.query_params:
        return

    # Visual feedback so you know the component loaded
    st.markdown("""
        <div id="auth-status" style="
            text-align: center; 
            padding: 10px; 
            background: #f0f9ff; 
            border-radius: 5px; 
            font-size: 0.8rem; 
            color: #666;
            margin-bottom: 10px;
            display: none;">
            🔄 Processing secure login...
        </div>
        <script>
            if (window.location.hash || window.parent.location.hash) {
                document.getElementById('auth-status').style.display = 'block';
            }
        </script>
    """, unsafe_allow_html=True)

    # JS Code: ROBUST REDIRECT
    js_code = """
    <script>
    (function() {
        console.log("VerbaPost: Auth Listener Starting...");
        
        function getHash() {
            try { return window.top.location.hash.substring(1); } catch(e) {}
            try { return window.parent.location.hash.substring(1); } catch(e) {}
            try { return window.location.hash.substring(1); } catch(e) {}
            return "";
        }

        function redirect(access_token, refresh_token) {
            console.log("VerbaPost: Redirecting...");
            try {
                // Try parent first (standard for Streamlit)
                const target = window.parent.location.href ? window.parent.location : window.location;
                const currentUrl = new URL(target.href);
                
                currentUrl.searchParams.set('access_token', access_token);
                if (refresh_token) currentUrl.searchParams.set('refresh_token', refresh_token);
                currentUrl.searchParams.set('type', 'oauth_callback');
                currentUrl.hash = ''; 
                
                target.href = currentUrl.toString();
            } catch (e) {
                console.error("VerbaPost: Redirect Failed", e);
            }
        }

        const hash = getHash();
        if (hash) {
            console.log("VerbaPost: Hash Found");
            const params = new URLSearchParams(hash);
            const access_token = params.get('access_token');
            const refresh_token = params.get('refresh_token');
            
            if (access_token) {
                redirect(access_token, refresh_token);
            }
        } else {
            console.log("VerbaPost: No Hash Found");
        }
    })();
    </script>
    """
    
    # Render with minimal height to ensure it stays in DOM
    components.html(js_code, height=1, width=1)