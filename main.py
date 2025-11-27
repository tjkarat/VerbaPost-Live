import streamlit as st

# --- 1. CONFIG ---
st.set_page_config(
    page_title="VerbaPost | Send Real Mail from Audio",
    page_icon="📮",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- 2. CSS ---
def inject_global_css():
    st.markdown("""
    <style>
        /* GLOBAL THEME */
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
        
        /* HERO HEADER */
        .custom-hero h1, .custom-hero div {
            color: white !important;
        }
        
        /* --- BUTTONS: THE NUCLEAR FIX --- */
        
        /* 1. Target the Paragraph <p> inside the Form Submit Button specifically */
        button[data-testid="stFormSubmitButton"] p {
            color: #FFFFFF !important;
            -webkit-text-fill-color: #FFFFFF !important; /* Webkit override */
            font-weight: bold !important;
        }
        
        /* 2. Target the Paragraph <p> inside any Primary Button */
        button[kind="primary"] p {
            color: #FFFFFF !important;
            -webkit-text-fill-color: #FFFFFF !important;
            font-weight: bold !important;
        }

        /* 3. Button Backgrounds (Blue Gradient) */
        button[data-testid="stFormSubmitButton"], 
        button[kind="primary"] {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%) !important;
            border: none !important;
            color: white !important;
        }

        /* 4. Hover Effects */
        button:hover {
            transform: scale(1.02);
        }

        /* SIDEBAR */
        [data-testid="stSidebar"] { 
            background-color: white !important; 
            border-right: 1px solid #e2e8f0; 
        }
        
        /* ANIMATION */
        @keyframes flyAcross {
            0% { transform: translateX(-200px); }
            100% { transform: translateX(110vw); }
        }
        .santa-sled {
            position: fixed; top: 20%; left: 0; font-size: 80px; z-index: 9999;
            animation: flyAcross 12s linear forwards; pointer-events: none;
        } 
    </style>
    """, unsafe_allow_html=True)

# --- 3. RUN ---
if __name__ == "__main__":
    inject_global_css()
    
    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "splash"
    
    try:
        import ui_main
        ui_main.show_main_app()
    except Exception as e:
        st.error(f"⚠️ Application Error: {e}")
        if st.button("Hard Reset App"):
            st.session_state.clear()
            st.rerun()