import streamlit as st

# --- EMBEDDED LOGOS (Base64 Data URIs) ---
# These are the actual image data strings. They function instantly without internet.

# Stripe (Blurple Wordmark)
STRIPE_B64 = "data:image/svg+xml;base64,PHN2ZyB2aWV3Qm94PSIwIDAgNjAgMjUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHBhdGggZD0iTTU5LjYgMTMuOGMtLjEgMC0uMiAwLS4zLjF2Ni44aC0zLjR2LTguOGgzLjR2MS4yYy43LTEgMS44LTEuNCAzLTEuNCAwIDAgLjEgMCAuMSAwVjEzLjh6bS01Ny4xIDMuOWMuNyAxLjcgMi4zIDIuNiA0LjEgMi42IDIuMyAwIDMuOS0xLjIgMy45LTMuMSAwLTEuNy0xLjMtMi41LTMuNS0zLjMtMi4xLS44LTMuMi0xLjQtMy4yLTIuOCAwLTEuNSAxLjMtMi41IDMuNS0yLjUgMS45IDAgMy40LjkgMy45IDIuNGwyLjktMS44QzEzLjIgNy4zIDEwLjggNiA3IDYgMy4yIDYgMCA4LjMgMCAxMi40YzAgMyAxLjkgNC42IDUuMiA1LjcgMi4yLjggMi43IDEuNSAyLjcgMi40IDAgMS4xLTEuMyAxLjctMy4xIDEuNy0yLjMgMC0zLjgtMS4zLTQuNC0zTDIuNSAxNy43ek0zNi4yIDZ2MTEuMmgyLjR2Mi42aC01LjhWNmgzLjR6bS04LjggMTQuNmMtMi4xIDAtMy43LTEuNy0zLjctNC4xIDAtMi40IDEuNS00LjEgMy43LTQuMSAxLjEgMCAyLjEuNSAyLjYgMS40di01LjJoMy40djEyLjVoLTMuNHYtMS4xYy0uNi45LTEuNSAxLjUtMi42IDEuNXptLjQtMi41Yy45IDAgMS42LS41IDItMS4zdi0yLjhjLS40LS44LTEuMS0xLjMtMi0xLjMtMS4xIDAtMS45LjktMS45IDIuNyAwIDEuOC44IDIuNyAxLjkgMi43em0xMC4yIDMuOGMtMS4zIDAtMi4zLS4zLTMtLjh2LTIuOWMuOC41IDEuOC45IDIuOC45IDEuMSAwIDEuNS0uNCAxLjUtLjk2IDAtLjU3LS40LS44My0xLjU4LTEuMTUtMS43Ni0uNDYtMy4zNS0xLjI2LTMuMzUtMy43MiAwLTEuOTcgMS41Mi0zLjM3IDMuNzYtMy4zNyAxLjIyIDAgMi4xNi4zMiAyLjc4LjZsLS42IDIuNWMtLjctLjQtMS41My0uNy0yLjM4LS43LS45IDAtMS4yNi4zNi0xLjI2Ljg3IDAgLjUzLjM3LjgxIDEuNjQgMS4yMSAxLjguNTcgMy4yOCAxLjQ2IDMuMjggMy43IDAgMi4xLTEuNiAzLjQxLTMuNjggMy40MXptMTUuMiAwaC0zLjR2LTEuMWMtLjUuOS0xLjUgMS41LTIuNiAxLjUtMi4xIDAtMy43LTEuNy0zLjctNC4xIDAtMi40IDEuNS00LjEgMy43LTQuMSAxLjEgMCAyLjEuNSAyLjYgMS40di01LjJoMy40djEyLjV6bS01LjYtMS4zYy45IDAgMS42LS41IDItMS4zdi0yLjhjLS40LS44LTEuMS0xLjMtMi0xLjMtMS4xIDAtMS45LjktMS45IDIuNyAwIDEuOC44IDIuNyAxLjkgMi43em0tMzYuMy0uNmwtMy40IDEuOVY2aDMuNHYxMS45eiIgZmlsbD0iIzYzN0MyQyIvPjwvc3ZnPg=="

# Twilio (Red Circle)
TWILIO_B64 = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAzMCAzMCI+PHBhdGggZmlsbD0iI0YyMjkzRCIgZD0iTTE1IDBDNi43MTYgMCAwIDYuNzE2IDAgMTVzNi43MTYgMTUgMTUgMTUgMTUtNi43MTYgMTUtMTVTMjMuMjg0IDAgMTUgMHptMCAyNi4yNWMtNi4yMTMgMC0xMS4yNS01LjAzNy0xMS4yNS0xMS4yNVM4Ljc4NyAzLjc1IDE1IDMuNzUgMjYuMjUgOC43ODcgMjYuMjUgMTUgMjEuMjEzIDI2LjI1IDE1IDI2LjI1eiIvPjxjaXJjbGUgZmlsbD0iI0YyMjkzRCIgY3g9IjE1IiBjeT0iMTUiIHI9IjUuMjUiLz48L3N2Zz4="

# OpenAI (Black Swirl)
OPENAI_B64 = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0iIzQxMjkyMSI+PHBhdGggZD0iTTIyLjI4MTkgOS44MjExYTUuOTk3OCA1Ljk5NzggMCAwIDAtLjQ3NjUtNC44ODc5IDYuMDA3IDYuMDA3IDAgMCAwLTQuMDg1OS0zLjA2NTkgOC45MzcgOC45MzcgMCAwIDAtOC45MjcxLjE3NDEgNi4wMDM5IDYuMDAzOSAwIDAgMC0zLjcwMzYgMS45OCBFLjAxMjUgNi4wMTI1IDAgMCAwIDkuNTQ0NSAxMi43NyA4LjkyNjcgOC45MjY3IDAgMCAwIDExLjc1NyAyMS41NzFBNS45OTU5IDUuOTk1OSAwIDAgMCAxNi44ODMxIDIxYTYuMDAxNiA2LjAwMTYgMCAwIDAgMy43OTA2LTEuOTAxOCA1Ljk5OTEgNS45OTkxIDAgMCAwIDEuMjQwMi00Ljk0MDMgOC45NDIgOC45NDIgMCAwIDAgLjM2OC00LjMzNjh6bS0zLjY2MDYgOC44NDY2YTQuNDQ0IDQuNDQ0IDAgMCAxLTIuNjkwNiAxLjQ1NTNsLTEuOTU4LS40MDk3YTEuNDUyNiAxLjQ1MjYgMCAwIDAtLjQ3MS0yLjgyNjdsMS4yODkyLjkzNDYgNC4wNjUzLjg0NTh6Ii8+PC9zdmc+"

# Supabase (Emerald Green Bolt)
SUPABASE_B64 = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0iIzNDQ0Y4RSI+PHBhdGggZD0iTTEyIDBDNS4zNzMgMCAwIDUuMzczIDAgMTJzNS4zNzMgMTIgMTIgMTIgMTItNS4zNzMgMTItMTJTMTguNjI3IDAgMTIgMHptMS4yIDUuNGwzLjYgNkg5LjZ2Ny4ybC0zLjYtNmg3LjJWNS40eiIvPjwvc3ZnPg=="

# USPS (Blue Eagle Symbol)
USPS_B64 = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA1MCA1MCI+PHBhdGggZmlsbD0iIzMzMzM2NiIgZD0iTTI1IDBDMTEuMiAwIDAgMTEuMiAwIDI1czExLjIgMjUgMjUgMjUgMjUtMTEuMiAyNS0yNVMzOC44IDAgMjUgMHptMTQuMyAxNS4xbC05LjYgMjAuNi0xOS4zLTguNyA5LjctMjAuNiAxOS4yIDguN3oiLz48L3N2Zz4="

def render_splash_page():
    """
    Renders the professional landing page for VerbaPost.
    """
    # --- CSS ---
    st.markdown("""
    <style>
    .block-container { padding-top: 2rem !important; padding-bottom: 3rem; max-width: 900px; }
    .hero-container { background-color: #ffffff; width: 100%; padding: 4rem 1rem; text-align: center; border-bottom: 1px solid #eaeaea; margin-bottom: 2rem; }
    .hero-title { font-family: 'Merriweather', serif; font-weight: 700; color: #111; font-size: clamp(2.5rem, 6vw, 4.5rem); margin-bottom: 0.5rem; letter-spacing: -1px; line-height: 1.1; }
    .hero-subtitle { font-family: 'Helvetica Neue', sans-serif; font-size: clamp(1rem, 3vw, 1.4rem); font-weight: 300; color: #555; margin-bottom: 2rem; margin-top: 1rem; max-width: 700px; margin-left: auto; margin-right: auto; line-height: 1.5; }
    
    .trust-container { 
        text-align: center; 
        padding: 30px 0; 
        margin-top: 40px; 
        display: flex; 
        flex-wrap: wrap; 
        justify-content: center; 
        align-items: center; 
        gap: 40px; 
        opacity: 0.85;
    }
    
    /* LOGO STYLING */
    .trust-logo { 
        height: 35px; /* Standardized height */
        width: auto;
        object-fit: contain;
        filter: grayscale(100%); 
        transition: all 0.3s ease; 
        opacity: 0.7; 
    }
    .trust-logo:hover { 
        filter: grayscale(0%); 
        opacity: 1.0; 
        transform: scale(1.05);
    }
    
    .secondary-link { text-align: center; margin-top: 50px; padding-top: 20px; border-top: 1px dashed #ddd; }
    .secondary-text { font-size: 0.9rem; color: #888; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

    # --- HERO SECTION ---
    st.markdown("""
    <div class="hero-container">
        <div class="hero-title">The Family Archive</div>
        <div class="hero-subtitle">
            Don't let their stories fade.<br>
            We interview your parents over the phone, transcribe their memories, and mail you physical keepsake letters.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- PRIMARY CTA (ARCHIVE) ---
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("📚 Start Your Family Archive", type="primary", use_container_width=True):
            if st.session_state.get("authenticated"):
                st.session_state.app_mode = "heirloom"
            else:
                st.session_state.app_mode = "login"
                st.session_state.redirect_to = "heirloom"
            st.rerun()

    # --- TRUST BADGES (USING EMBEDDED STRINGS) ---
    # We inject the python string variables directly into the HTML format string
    st.markdown(f"""
    <div style="text-align: center; margin-top: 50px; margin-bottom: 10px;">
        <small style="font-size: 0.75rem; letter-spacing: 1.5px; text-transform: uppercase; color: #999; font-weight: 600;">Secure Infrastructure</small>
    </div>
    <div class="trust-container">
        <img class="trust-logo" src="{STRIPE_B64}" title="Stripe Payments" style="height: 30px;">
        <img class="trust-logo" src="{TWILIO_B64}" title="Twilio Voice" style="height: 32px;">
        <img class="trust-logo" src="{OPENAI_B64}" title="OpenAI Intelligence" style="height: 28px;">
        <img class="trust-logo" src="{SUPABASE_B64}" title="Supabase Database" style="height: 30px;">
        <img class="trust-logo" src="{USPS_B64}" title="USPS Delivery" style="height: 38px;">
    </div>
    """, unsafe_allow_html=True)

    # --- SECONDARY OPTION (VENDING MACHINE) ---
    st.markdown("<div class='secondary-link'><div class='secondary-text'>Looking to send a single letter?</div></div>", unsafe_allow_html=True)
    
    col_sec1, col_sec2, col_sec3 = st.columns([1, 1, 1])
    with col_sec2:
        if st.button("📮 Go to Letter Store", use_container_width=True):
            # CRITICAL FIX: Ensure we explicitly switch mode to utility
            st.query_params["mode"] = "utility"
            
            if st.session_state.get("authenticated"):
                st.session_state.app_mode = "main" 
            else:
                st.session_state.app_mode = "login"
                st.session_state.redirect_to = "main" 
            st.rerun()

    # --- FOOTER ---
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # NAVIGATION (FIXED KEYS)
    c_blog, c_legal = st.columns(2)
    with c_blog:
         if st.button("📰 Read our Blog", use_container_width=True, key="splash_foot_blog"):
             st.session_state.app_mode = "blog"
             st.rerun()
    with c_legal:
         if st.button("⚖️ Legal / Terms", use_container_width=True, key="splash_foot_legal"):
            st.session_state.app_mode = "legal"
            st.rerun()

    st.markdown("<div style='text-align: center; color: #ccc; font-size: 0.75rem; border-top: 1px solid #f0f0f0; padding-top: 20px; margin-top: 20px;'>VerbaPost • Private • Secure • Forever</div>", unsafe_allow_html=True)
    
    return ""