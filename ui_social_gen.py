import streamlit as st

def render_social_card():
    """
    Renders a pixel-perfect 1200x630 social media card for VerbaPost.
    INSTRUCTIONS: Run this, set your browser to 100% zoom, and screenshot the card container.
    """
    st.set_page_config(layout="wide", page_title="Social Card Generator")
    
    # --- OG IMAGE CSS (1200x630px) ---
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Merriweather:wght@700&family=Helvetica+Neue:wght@400;600&display=swap');
    
    .main { background-color: #333; } /* Dark background to frame the card */
    
    .og-card {
        width: 1200px;
        height: 630px;
        background-color: #ffffff;
        margin: 50px auto;
        padding: 60px;
        border: 1px solid #ddd;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        position: relative;
        box-shadow: 0 20px 50px rgba(0,0,0,0.5);
    }
    
    .og-border {
        position: absolute;
        top: 20px; left: 20px; right: 20px; bottom: 20px;
        border: 2px solid #d93025; /* VerbaPost Red */
        opacity: 0.1;
        pointer-events: none;
    }

    .og-title {
        font-family: 'Merriweather', serif;
        font-size: 110px;
        font-weight: 700;
        color: #111;
        margin-bottom: 10px;
        letter-spacing: -2px;
    }
    
    .og-subtitle {
        font-family: 'Helvetica Neue', sans-serif;
        font-size: 40px;
        font-weight: 600;
        color: #d93025;
        text-transform: uppercase;
        letter-spacing: 4px;
        margin-bottom: 40px;
    }
    
    .og-tagline {
        font-family: 'Helvetica Neue', sans-serif;
        font-size: 32px;
        color: #555;
        font-weight: 300;
        max-width: 800px;
        text-align: center;
        line-height: 1.4;
    }

    .og-footer {
        position: absolute;
        bottom: 50px;
        font-family: 'Courier New', monospace;
        color: #aaa;
        font-size: 24px;
    }
    </style>
    """, unsafe_allow_html=True)

    # --- RENDER CARD ---
    st.markdown("""
    <div class="og-card">
        <div class="og-border"></div>
        <div class="og-title">VerbaPost</div>
        <div class="og-subtitle">Real Mail Gets Read</div>
        <div class="og-tagline">
            "Don't know how to start? Speak it first, and we'll transcribe."<br>
            <br>
            <strong>Voice-to-Letter • Family Archive • Certified Mail</strong>
        </div>
        <div class="og-footer">verbapost.com</div>
    </div>
    """, unsafe_allow_html=True)
    
    return ""

if __name__ == "__main__":
    render_social_card()
