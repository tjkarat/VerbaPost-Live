import streamlit.components.v1 as components

def inject_ga():
    # REPLACE 'G-XXXXXXXXXX' with your actual Measurement ID from Google Analytics
    measurement_id = 'G-XXXXXXXXXX' 
    
    ga_code = f"""
    <script async src="https://www.googletagmanager.com/gtag/js?id={measurement_id}"></script>
    <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){{dataLayer.push(arguments);}}
        gtag('js', new Date());
        gtag('config', '{measurement_id}');
    </script>
    """
    components.html(ga_code, height=0)
