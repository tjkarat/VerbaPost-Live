import streamlit as st
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
from typing import Type, Any, Tuple, Dict
import uuid

# Global placeholder variables
Engine = None
SessionLocal = None
Base = None
Models: Dict[str, Any] = {} # Global registry for model classes

# --- 1. INITIALIZE DATABASE SETUP (Lazy Loading) ---
@st.cache_resource(ttl=3600) # Cache for 1 hour
def initialize_database() -> Tuple[Any, Any, Any, Dict[str, Any]]:
    global Engine, SessionLocal, Base, Models
    
    if Engine is not None and Models:
        return Engine, SessionLocal, Base, Models

    if "DATABASE_URL" in st.secrets:
        db_url = st.secrets["DATABASE_URL"].replace("postgres://", "postgresql://")
    else:
        print("⚠️ WARNING: No DATABASE_URL found. Using temporary SQLite.")
        db_url = "sqlite:///local_dev.db"

    try:
        Engine = create_engine(db_url, pool_pre_ping=True)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=Engine)
        Base = declarative_base()
        
    except Exception as e:
        print(f"❌ Database Engine Error: {e}")
        Engine = create_engine("sqlite:///") 
        SessionLocal = sessionmaker(bind=Engine)
        Base = declarative_base()
        st.error("System Error: Could not connect to Database.")
        return Engine, SessionLocal, Base, {}

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
        status = Column(String, default="Draft") 
        tier = Column(String)
        price = Column(String)
        created_at = Column(DateTime, default=datetime.utcnow)
    
    # Store models in a dictionary for easy, stable access
    Models = {'user_profiles': UserProfile, 'letter_drafts': LetterDraft}
        
    # --- 3. AUTO-CREATE TABLES ---
    try:
        Base.metadata.create_all(bind=Engine)
        print("✅ Database Tables Verified")
    except Exception as e:
        print(f"❌ Error Creating Tables: {e}")
        
    return Engine, SessionLocal, Base, Models

# Call the initialization function to set up global variables on import
initialize_database()

# --- 4. HELPER FUNCTIONS ---

def get_session():
    """Returns a new session instance."""
    return SessionLocal()

def get_model(name: str) -> Type[Any]:
    """Retrieves model class from the custom global registry."""
    if not Models:
        initialize_database()
    return Models.get(name)

def get_user_profile(email):
    """Fetches user details to pre-fill forms."""
    UserProfile = get_model('user_profiles')
    if not UserProfile: return None
    db = get_session()
    try:
        return db.query(UserProfile).filter(UserProfile.email == email).first()
    except Exception:
        return None
    finally:
        db.close()

def save_draft(email, text, tier, price, status="Draft", address_data=None):
    """Saves or updates a draft letter."""
    LetterDraft = get_model('letter_drafts')
    if not LetterDraft: return None
    
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
    UserProfile = get_model('user_profiles')
    if not UserProfile: return None
    
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