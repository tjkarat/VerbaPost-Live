# --- GLOBAL STYLES (FORCE LIGHT MODE & ANALYTICS) ---
GA_ID = "G-D3P178CESF"
st.markdown(f"""
    <script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
    <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){{dataLayer.push(arguments);}}
        gtag('js', new Date());
        gtag('config', '{GA_ID}');
    </script>
    <style>
    /* Force Light Theme Background */
    [data-testid="stAppViewContainer"] {{
        background-color: #ffffff;
    }}
    [data-testid="stSidebar"] {{
        background-color: #f8f9fa;
    }}
    
    /* Force Text Colors to Dark Grey (General) */
    h1, h2, h3, h4, h5, h6, p, li, div, label, span {{
        color: #31333F !important;
    }}
    
    /* --- BUTTON FIX START --- */
    
    /* Normal Buttons (Secondary) */
    div.stButton > button {{
        background-color: #ffffff !important;
        color: #31333F !important;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
    }}
    
    /* Primary Buttons (Red/Blue - Like Log In) */
    /* We force the TEXT (p) inside the button to be WHITE */
    button[kind="primary"] {{
        background-color: #2a5298 !important;
        border: none !important;
    }}
    button[kind="primary"] p {{
        color: #FFFFFF !important;
    }}
    button[kind="primary"]:hover {{
        background-color: #1e3c72 !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }}
    
    /* --- BUTTON FIX END --- */
    
    /* Fix Input Fields */
    input, textarea, select {{
        color: #31333F !important;
        background-color: #ffffff !important;
        border: 1px solid #e0e0e0 !important;
    }}
    
    /* Hide Default Streamlit Elements */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    </style>
""", unsafe_allow_html=True)