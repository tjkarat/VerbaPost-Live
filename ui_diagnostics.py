import streamlit as st
import os
import json
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("UI_DIAG")

try:
    import secrets_manager
except ImportError:
    secrets_manager = None

def get_target_url():
    """Logic to replicate how the app finds the DB URL"""
    if secrets_manager:
        url = secrets_manager.get_secret("SUPABASE_DB_URL") or secrets_manager.get_secret("DATABASE_URL")
        if url: return url
    
    # Fallback to Env
    return os.environ.get("SUPABASE_DB_URL") or os.environ.get("DATABASE_URL")

def render_diagnostic_page():
    st.title("🩺 Database Diagnostics")
    st.warning("This tool writes test data directly to your production database.")

    target_url = get_target_url()
    
    if not target_url:
        st.error("❌ CRITICAL: No Database URL found in Secrets or Environment.")
        return

    # Mask the password for display
    safe_url = target_url.split("@")[-1] if "@" in target_url else "HIDDEN"
    st.info(f"Targeting: `{safe_url}`")

    if st.button("🚀 Run Connectivity & Data Test"):
        run_tests(target_url)

def run_tests(db_url):
    results_container = st.container()
    
    try:
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        st.toast("Connection Established")
    except Exception as e:
        st.error(f"❌ Connection Failed: {e}")
        return

    test_id = None

    # --- TEST 1: INSERT ---
    with results_container:
        st.markdown("### 1. Insert Test")
        try:
            # We explicitly ask for ID to be returned
            insert_sql = text("""
                INSERT INTO letter_drafts (user_email, content, status, tier, price)
                VALUES (:email, :content, :status, :tier, :price)
                RETURNING id;
            """)
            
            result = session.execute(insert_sql, {
                "email": "diag_tool@verbapost.com",
                "content": "Diagnostic Test Row",
                "status": "TEST_MODE",
                "tier": "Standard",
                "price": 0.00
            })
            session.commit()
            
            row = result.fetchone()
            if row:
                test_id = row[0]
                st.success(f"✅ INSERT SUCCESS. Created ID: `{test_id}` (Type: `{type(test_id)}`)")
            else:
                st.error("❌ INSERT FAILED. No ID returned.")
                return
        except Exception as e:
            st.error(f"❌ INSERT EXCEPTION: {e}")
            return

    # --- TEST 2: READ ---
    with results_container:
        st.markdown(f"### 2. Read Test (ID: {test_id})")
        try:
            # Check Integer
            read_sql = text("SELECT id, content FROM letter_drafts WHERE id = :id")
            
            try:
                res_int = session.execute(read_sql, {"id": int(test_id)}).fetchone()
                if res_int:
                    st.success(f"✅ FOUND via INTEGER lookup: {res_int}")
                else:
                    st.warning("⚠️ FAILED via INTEGER lookup")
            except:
                st.warning("⚠️ INTEGER lookup raised exception (Type Error?)")

            # Check String
            res_str = session.execute(read_sql, {"id": str(test_id)}).fetchone()
            if res_str:
                st.success(f"✅ FOUND via STRING lookup: {res_str}")
            else:
                st.warning("⚠️ FAILED via STRING lookup")

        except Exception as e:
            st.error(f"❌ READ EXCEPTION: {e}")

    # --- TEST 3: UPDATE ---
    with results_container:
        st.markdown("### 3. Update Test")
        try:
            update_sql = text("""
                UPDATE letter_drafts
                SET content = :new_content, recipient_data = :rd
                WHERE id = :id
            """)
            
            new_data = json.dumps({"name": "Diag User", "street": "123 Test Ln"})
            
            # Try updating as String (since that is what failed in your app)
            result = session.execute(update_sql, {
                "new_content": "UPDATED BY DIAGNOSTIC",
                "rd": new_data,
                "id": str(test_id) 
            })
            session.commit()
            
            if result.rowcount > 0:
                st.success(f"✅ UPDATE SUCCESS (String ID). Rows affected: {result.rowcount}")
                
                # Verify Data Persistence
                verify_sql = text("SELECT recipient_data FROM letter_drafts WHERE id = :id")
                saved_data = session.execute(verify_sql, {"id": str(test_id)}).scalar()
                st.info(f"Saved Data Verification: `{saved_data}`")
            else:
                st.error(f"❌ UPDATE FAILED (String ID). Rows affected: 0")
                
                # Retry as Integer
                result_retry = session.execute(update_sql, {
                    "new_content": "UPDATED BY DIAGNOSTIC (RETRY)",
                    "rd": new_data,
                    "id": int(test_id)
                })
                session.commit()
                if result_retry.rowcount > 0:
                    st.success(f"✅ UPDATE SUCCESS (Integer ID). Rows affected: {result_retry.rowcount}")
                else:
                    st.error(f"❌ UPDATE FAILED (Integer ID). Rows affected: 0")

        except Exception as e:
            st.error(f"❌ UPDATE EXCEPTION: {e}")

    session.close()
