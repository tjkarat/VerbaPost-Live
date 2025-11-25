import streamlit as st
import pandas as pd

# --- SAFETY IMPORTS ---
try: import database
except ImportError: database = None

try: import letter_format
except ImportError: letter_format = None

try: import ai_engine
except ImportError: ai_engine = None

try: import analytics
except ImportError: analytics = None

def show_admin():
    st.title("🔐 Admin Console")
    
    # --- DIAGNOSTICS ROW ---
    c1, c2, c3 = st.columns(3)
    c1.metric("Database", "✅ Connected" if database else "❌ Missing")
    c2.metric("PDF Engine", "✅ Active" if letter_format else "❌ Missing")
    c3.metric("GA4", "✅ Active" if analytics else "❌ Missing")
    
    st.divider()

    # --- TABS ---
    tab_mail, tab_users, tab_config = st.tabs(["🖨️ Mailroom", "👥 Users", "⚙️ Config"])
    
    # --- TAB 1: MAILROOM ---
    with tab_mail:
        st.subheader("Pending Letters")
        
        if database:
            # 1. Fetch Data
            letters = database.fetch_pending_letters()
            
            if letters:
                # Convert to DataFrame for easy viewing
                df = pd.DataFrame(letters)
                
                # Show Data Table
                st.dataframe(
                    df, 
                    column_config={
                        "created_at": "Date",
                        "tier": "Service Tier",
                        "status": "Status",
                        "price": st.column_config.NumberColumn("Price", format="$%.2f")
                    },
                    use_container_width=True
                )
                
                st.write("---")
                
                # 2. Print Control Panel
                st.subheader("🖨️ Print Manager")
                
                # ERROR FIX: We use .get() to safely handle missing emails or tiers
                letter_options = {
                    row['id']: f"{row.get('created_at', 'Date?')} - {row.get('user_email', 'Unknown User')} ({row.get('tier', 'Standard')})" 
                    for row in letters
                }
                
                selected_id = st.selectbox("Select Letter to Print", options=list(letter_options.keys()), format_func=lambda x: letter_options[x])
                
                if selected_id:
                    # Find the specific letter data
                    letter_data = next((item for item in letters if item["id"] == selected_id), None)
                    
                    if letter_data and letter_format:
                        # Generate the PDF
                        # We use .get() here too to be safe
                        pdf_bytes = letter_format.create_pdf(
                            body_text=letter_data.get("body_text", ""),
                            recipient_info=f"{letter_data.get('recipient_name', '')}\n{letter_data.get('recipient_street', '')}", 
                            sender_info="VerbaPost Sender",      
                            is_heirloom=("Heirloom" in letter_data.get("tier", ""))
                        )
                        
                        # DOWNLOAD BUTTON
                        st.download_button(
                            label="📄 Download PDF for Printing",
                            data=pdf_bytes,
                            file_name=f"letter_{selected_id}.pdf",
                            mime="application/pdf",
                            type="primary"
                        )
                        
                        if st.button("Mark as Sent"):
                            database.mark_as_sent(selected_id)
                            st.success("Status Updated!")
                            st.rerun()
            else:
                st.info("📭 No pending letters found.")
        else:
            st.error("Database connection missing.")

    with tab_users:
        st.info("User metrics coming soon.")

    with tab_config:
        if analytics: analytics.show_analytics()