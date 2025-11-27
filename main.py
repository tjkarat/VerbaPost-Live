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
def inject_global_css():
    st.markdown("""
    <style>
        /* GLOBAL THEME: Professional Paper & Ink */
        .stApp { background-color: #f8f9fc; }
        
        /* TEXT COLORS */
        h1, h2, h3, h4, h5, h6, .stMarkdown, p, li, span, div { 
            color: #2d3748 !important; 
        }
/* --- HERO HEADER (Blue Box) --- */
        .custom-hero h1, .custom-hero div {
            color: white !important;
        }
        /* INPUT LABELS - BRAND BLUE FIX */
        label, .stTextInput label, .stSelectbox label {
            color: #2a5298 !important;
            font-weight: 600 !important;
        }
        
        /* INPUT BOXES: White BG, Brand Blue Text */
        .stTextInput input, .stTextArea textarea, .stSelectbox div, div[data-baseweb="select"] > div {
            background-color: #ffffff !important; 
            color: #2a5298 !important; /* Brand Blue text for readability */
            border: 1px solid #cbd5e0 !important;
            border-radius: 8px;
        }
        
        /* BUTTONS: Gradient Blue */
        div.stButton > button {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white !important; 
            border: none; 
            border-radius: 25px; 
            padding: 0.5rem 1.5rem;
            font-weight: 600;
            transition: transform 0.1s;
        }
        div.stButton > button:hover {
            transform: scale(1.02);
            color: white !important;
        }
        
        /* SECONDARY BUTTONS */
        div.stButton > button[kind="secondary"] {
            background: white; 
            color: #2a5298 !important; 
            border: 2px solid #2a5298;
        }

        /* SIDEBAR */
        [data-testid="stSidebar"] { 
            background-color: white !important; 
            border-right: 1px solid #e2e8f0; 
        }
        
        /* SANTA ANIMATION KEYFRAMES */
        @keyframes flyAcross {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(150%); }
        }
        .santa-sled {
            position: fixed;
            top: 20%;
            left: -100px;
            font-size: 80px;
            z-index: 9999;
            animation: flyAcross 4s linear forwards;
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