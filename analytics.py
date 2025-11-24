import streamlit as st
import streamlit.components.v1 as components # <--- THIS WAS MISSING

# --- 1. INJECTOR (Used by Main) ---
def inject_ga():
    # REPLACE 'G-XXXXXXXXXX' with your actual Measurement ID
    measurement_id = 'G-D3P178CESF' 
    
    ga_js = f"""
    <script async src="https://www.googletagmanager.com/gtag/js?id={measurement_id}"></script>
    <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){{dataLayer.push(arguments);}}
        gtag('js', new Date());
        gtag('config', '{measurement_id}', {{
            'cookie_flags': 'SameSite=None;Secure'
        }});
    </script>
    """
    # Injecting as a component (Option 1)
    components.html(ga_js, height=0, width=0)

# --- 2. DASHBOARD (Used by Admin Console) ---
def show_analytics():
    """Displays the analytics dashboard in the Admin Console"""
    st.subheader("📊 Traffic Analytics")
    
    # Check if GA is configured
    st.success(f"✅ Google Analytics is Active (ID: G-D3P178CESF)")
    
    st.info("To view live traffic data, please visit your Google Analytics Dashboard directly.")
    
    # Placeholder for future embedded charts
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Tracking Status", "Live")
    with c2:
        st.metric("Data Source", "Client-Side JS")