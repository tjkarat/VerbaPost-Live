def check_is_admin():
    """Checks for admin privileges using FLAT secrets"""
    if not st.session_state.get("user"):
        return False
        
    try:
        # 1. Get Admin Email (Try Flat first, then Nested)
        admin_email = ""
        if "ADMIN_EMAIL" in st.secrets:
            admin_email = st.secrets["ADMIN_EMAIL"]
        elif "admin" in st.secrets and "email" in st.secrets["admin"]:
            admin_email = st.secrets["admin"]["email"]
            
        if not admin_email: return False

        # 2. Compare with Current User
        user_obj = st.session_state.user
        current_email = ""
        
        if hasattr(user_obj, "email") and user_obj.email: 
            current_email = user_obj.email
        elif hasattr(user_obj, "user") and hasattr(user_obj.user, "email"): 
            current_email = user_obj.user.email
        elif isinstance(user_obj, dict) and "email" in user_obj: 
            current_email = user_obj["email"]
            
        return current_email.strip().lower() == admin_email.strip().lower()
        
    except Exception as e:
        print(f"Admin Check Error: {e}")
        return False