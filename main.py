import streamlit as st

st.set_page_config(
    page_title="VerbaPost | Send Real Mail from Audio",
    page_icon="📮",
    layout="centered",
    initial_sidebar_state="expanded"
)

def inject_global_css():
    st.markdown("""
    <style>
        .stApp { background-color: #f8f9fc; }
        
        h1, h2, h3, h4, h5, h6, .stMarkdown, p, li, span, div { 
            color: #2d3748 !important; 
        }
        
        /* ... (Keep your other CSS) ... */

        /* BUTTON FIXES */
        div.stButton > button p { color: #2a5298 !important; }
        
        div.stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%) !important;
            border: none !important;
        }
        div.stButton > button[kind="primary"] p { color: white !important; }

        /* FIX 3: Form Submit Button (Login) */
        button[data-testid="stFormSubmitButton"] {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%) !important;
            border: none !important;
        }
        button[data-testid="stFormSubmitButton"] p {
            color: white !important;
        }

        /* Hover Effects */
        div.stButton > button:hover, button[data-testid="stFormSubmitButton"]:hover {
            transform: scale(1.02);
        }
    </style>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    inject_global_css()
    if "app_mode" not in st.session_state: st.session_state.app_mode = "splash"
    try:
        import ui_main
        ui_main.show_main_app()
    except Exception as e:
        st.error(f"⚠️ Application Error: {e}")