import streamlit as st

# --- 1. CONFIG ---
# This MUST be the very first Streamlit command in the file.
st.set_page_config(
    page_title="VerbaPost | Send Real Mail from Audio",
    page_icon="📮",
    layout="centered",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'mailto:support@verbapost.com',
        'About': "# VerbaPost\nTurn your voice into real mail."
    }
)

# --- 2. CSS ---
# --- 2. CSS ---
def inject_global_css():
    st.markdown("""
    <style>
        /* GLOBAL THEME: Professional Paper & Ink */
        .stApp { background-color: #f8f9fc; }
        
        /* TEXT COLORS */
        h1, h2, h3, h4, h5, h6, .stMarkdown, p, li, span, div { 
            color: #2d3748 !important; 
        }

        /* INPUT LABELS */
        label, .stTextInput label, .stSelectbox label {
            color: #2a5298 !important;
            font-weight: 600 !important;
        }
        
        /* INPUT BOXES */
        .stTextInput > div > div, .stTextArea > div > div {
            background-color: #ffffff !important; 
            border: 1px solid #cbd5e0 !important;
            border-radius: 8px !important;
        }
        .stTextInput input, .stTextArea textarea {
            color: #2a5298 !important;
            -webkit-text-fill-color: #2a5298 !important;
            caret-color: #2a5298 !important;
        }
        
        /* HERO HEADER (Blue Box) */
        .custom-hero h1, .custom-hero div {
            color: white !important;
        }
        
        /* --- BUTTONS (The Fix) --- */
        
        /* 1. ALL Buttons default to Blue Text (Fixes the white-on-white issue) */
        div.stButton > button p {
            color: #2a5298 !important;
        }
        
        /* 2. Primary Buttons get the Blue Gradient Background */
        div.stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%) !important;
            border: none !important;
            transition: transform 0.1s;
        }
        
        /* 3. Primary Buttons get White Text (Overrides rule #1) */
        div.stButton > button[kind="primary"] p {
            color: white !important;
        }

        /* Hover Effects */
        div.stButton > button:hover {
            transform: scale(1.02);
        }

        /* SIDEBAR */
        [data-testid="stSidebar"] { 
            background-color: white !important; 
            border-right: 1px solid #e2e8f0; 
        }
        
      /* --- SANTA ANIMATION FIX --- */
        /* Use 'vw' (viewport width) instead of % to ensure he crosses the whole screen */
        @keyframes flyAcross {
            0% { transform: translateX(-200px); }
            100% { transform: translateX(110vw); } /* Flies 110% across the screen width */
        }
        .santa-sled {
            position: fixed;
            top: 20%;
            left: 0;
            font-size: 80px;
            z-index: 9999;
            animation: flyAcross 12s linear forwards; /* Increased to 12s for a slower, majestic pace */
            pointer-events: none;
        } 
    </style>
    """, unsafe_allow_html=True)

# --- 3. RUN ---
if __name__ == "__main__":
    inject_global_css()
    
    # Initialize Session State
    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "splash"
    
    try:
        # Lazy import to prevent circular dependency crash on startup
        import ui_main
        ui_main.show_main_app()
    except Exception as e:
        st.error(f"⚠️ Application Error: {e}")
        # Hard Reset button to clear stuck states
        if st.button("Hard Reset App"):
            st.session_state.clear()
            st.rerun()