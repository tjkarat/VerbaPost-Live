import streamlit as st
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import uuid

# Global placeholder variables
Engine = None
SessionLocal = None
Base = None

# --- 1. INITIALIZE DATABASE SETUP (Lazy Loading) ---
@st.cache_resource
def initialize_database():
    global Engine, SessionLocal, Base
    
    if Engine is not None:
        return Engine, SessionLocal, Base # Already initialized

    if "DATABASE_URL" in st.secrets:
        # Fix postgres:// compatibility for SQLAlchemy
        db_url = st.secrets["DATABASE_URL"].replace("postgres://", "postgresql://")
    else:
        print("⚠️ WARNING: No DATABASE_URL found. Using temporary SQLite.")
        db_url = "sqlite:///local_dev.db"

    try:
        Engine = create_engine(db_url, pool_pre_ping=True)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=Engine)
        Base = declarative_base()
        
        print("✅ Database Engine Initialized")
        
    except Exception as e:
        print(f"❌ Database Engine Error: {e}")
        st.error("System Error: Could not connect to Database.")
        Engine = create_engine("sqlite:///") 
        SessionLocal = sessionmaker(bind=Engine)
        Base = declarative_base()
        return Engine, SessionLocal, Base

    # --- 2. DEFINE TABLES (Models) ---

    class UserProfile(Base):
        __tablename__ = "user_profiles"
        
        id = Column(Integer, primary_key=True, index=True)
        email = Column(String, unique=True, index=True)
        full_name = Column(String)
        
        address_line1 = Column(String)
        address_city = Column(String)
        address_state = Column(String)
        address_zip = Column(String)
        
        created_at = Column(DateTime, default=datetime.utcnow)

    class LetterDraft(Base):
        __tablename__ = "letter_drafts"

        id = Column(Integer, primary_key=True, index=True)
        user_email = Column(String, index=True)
        
        transcription = Column(Text)
        status = Column(String, default="Draft") # Draft, Paid, Sent
        
        tier = Column(String)
        price = Column(String)
        created_at = Column(DateTime, default=datetime.utcnow)
        
    # --- 3. AUTO-CREATE TABLES ---
    try:
        Base.metadata.create_all(bind=Engine)
        print("✅ Database Tables Verified")
    except Exception as e:
        print(f"❌ Error Creating Tables: {e}")
        
    return Engine, SessionLocal, Base

# Call the initialization function at the top level
initialize_database()

# --- 4. HELPER FUNCTIONS ---

def get_session():
    """Returns a new session instance."""
    # Ensure initialization runs if not already
    if not Engine:
        initialize_database()
        
    return SessionLocal()


def get_user_profile(email):
    """Fetches user details to pre-fill forms."""
    # We must use the classes defined inside initialize_database()
    UserProfile = initialize_database()[2].metadata.tables['user_profiles'].class_
    
    db = get_session()
    try:
        return db.query(UserProfile).filter(UserProfile.email == email).first()
    except Exception:
        return None
    finally:
        db.close()

def save_draft(email, text, tier, price, status="Draft", address_data=None):
    """Saves or updates a draft letter."""
    LetterDraft = initialize_database()[2].metadata.tables['letter_drafts'].class_
    
    db = get_session()
    try:
        draft = LetterDraft(user_email=email, transcription=text, tier=tier, price=str(price), status=status)
        db.add(draft); db.commit(); db.refresh(draft)
        return draft.id
    except Exception as e:
        db.rollback(); return None
    finally:
        db.close()

def update_user_profile(email, name, street, city, state, zip_code, lang="English"):
    """Updates user address profile"""
    UserProfile = initialize_database()[2].metadata.tables['user_profiles'].class_
    
    db = get_session()
    try:
        user = db.query(UserProfile).filter(UserProfile.email == email).first()
        if not user:
            user = UserProfile(email=email)
            db.add(user)
        
        user.full_name = name
        user.address_line1 = street
        user.address_city = city
        user.address_state = state
        user.address_zip = zip_code
        
        db.commit()
    except Exception as e:
        print(f"Error updating profile: {e}")
    finally:
        db.close()