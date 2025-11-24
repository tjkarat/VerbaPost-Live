# --- GLOBAL STYLES (FORCE LIGHT MODE) ---
# Paste this right after the st.set_page_config line
st.markdown("""
    <style>
    /* Force Light Theme Background */
    [data-testid="stAppViewContainer"] {
        background-color: #ffffff;
    }
    [data-testid="stSidebar"] {
        background-color: #f8f9fa;
    }
    [data-testid="stHeader"] {
        background-color: rgba(0,0,0,0);
    }
    
    /* Force Text Colors */
    h1, h2, h3, h4, h5, h6, p, li, div {
        color: #31333F !important;
    }
    
    /* Fix Input Fields in Dark Mode Browsers */
    input, textarea, select {
        color: #31333F !important;
        background-color: #ffffff !important;
    }
    
    /* Hide Default Elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)