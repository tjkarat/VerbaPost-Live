import streamlit as st
import pandas as pd
import datetime

# Try importing database, handle failure gracefully
try: import database
except ImportError: database = None

def show_admin():
    st.title("🔐 Admin Console")
    st.markdown("Overview of VerbaPost operations.")

    if not database:
        st.error("⚠️ Database module not connected.")
        return

    # Create Tabs for layout
    tab1, tab2 = st.tabs(["📮 Letter Queue", "🔧 System Status"])

    with tab1:
        st.subheader("All Letters / Drafts")
        
        # We attempt to fetch data using standard Supabase/Database patterns.
        # This block is defensive: it tries to find the data without crashing the app.
        try:
            data = None
            
            # 1. Try generic fetch if method exists
            if hasattr(database, "fetch_all_letters"):
                data = database.fetch_all_letters()
            
            # 2. Else try accessing Supabase client directly (common pattern)
            elif hasattr(database, "supabase"):
                # "letters" or "drafts" are common table names. Adjust if yours differs.
                try:
                    response = database.supabase.table("letters").select("*").execute()
                    data = response.data
                except:
                    # Fallback to 'drafts' table if 'letters' fails
                    response = database.supabase.table("drafts").select("*").execute()
                    data = response.data

            # Render Data
            if data:
                df = pd.DataFrame(data)
                # Reorder columns for readability if 'created_at' exists
                if 'created_at' in df.columns:
                    df['created_at'] = pd.to_datetime(df['created_at'])
                    df = df.sort_values(by='created_at', ascending=False)
                
                st.dataframe(df, use_container_width=True)
                
                st.markdown("### Action Menu")
                selected_id = st.text_input("Enter Letter ID to Update Status")
                new_status = st.selectbox("New Status", ["sent_api", "processed", "heirloom_printed", "error"])
                
                if st.button("Update Status"):
                    if hasattr(database, "update_letter_status"):
                        database.update_letter_status(selected_id, new_status)
                        st.success(f"Updated {selected_id} to {new_status}")
                        st.rerun()
                    elif hasattr(database, "supabase"):
                        database.supabase.table("letters").update({"status": new_status}).eq("id", selected_id).execute()
                        st.success("Updated via raw Supabase connection")
                        st.rerun()
            else:
                st.info("No letters found in database yet.")
                
        except Exception as e:
            st.warning(f"Could not load letter data automatically: {e}")
            st.write("Debug - Available database methods:", [m for m in dir(database) if not m.startswith("__")])

    with tab2:
        st.subheader("System Health")
        st.json({
            "Streamlit Version": st.__version__,
            "Database Module": "Connected" if database else "Disconnected",
            "Time": str(datetime.datetime.now())
        })