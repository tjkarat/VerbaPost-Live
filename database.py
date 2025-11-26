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
Models: Dict[str, Any] = {} 

# --- 1. INITIALIZE DATABASE SETUP ---
@st.cache_resource(ttl=3600)
def initialize_database() -> Tuple[Any, Any, Any, Dict[str, Any]]:
    global Engine, SessionLocal, Base, Models
    
    if Engine is not None and Models:
        return Engine, SessionLocal, Base, Models

    if "DATABASE_URL" in st.secrets:
        db_url = st.secrets["DATABASE_URL"].replace("postgres://", "postgresql://")
    else:
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
        return Engine, SessionLocal, Base, {}

    # --- MODELS ---
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
    
    Models = {'user_profiles': UserProfile, 'letter_drafts': LetterDraft}
        
    try:
        Base.metadata.create_all(bind=Engine)
    except Exception as e:
        print(f"❌ Error Creating Tables: {e}")
        
    return Engine, SessionLocal, Base, Models

initialize_database()

# --- HELPER FUNCTIONS ---

def get_session():
    if not Engine: initialize_database()
    return SessionLocal()

def get_model(name: str):
    if not Models: initialize_database()
    return Models.get(name)

def get_user_profile(email):
    UserProfile = get_model('user_profiles')
    if not UserProfile: return None
    db = get_session()
    try:
        return db.query(UserProfile).filter(UserProfile.email == email).first()
    except: return None
    finally: db.close()

def save_draft(email, text, tier, price, status="Draft", address_data=None):
    LetterDraft = get_model('letter_drafts')
    if not LetterDraft: return None
    db = get_session()
    try:
        draft = LetterDraft(user_email=email, transcription=text, tier=tier, price=str(price), status=status)
        db.add(draft); db.commit(); db.refresh(draft)
        return draft.id
    except: db.rollback(); return None
    finally: db.close()

def update_user_profile(email, name, street, city, state, zip_code):
    UserProfile = get_model('user_profiles')
    if not UserProfile: return None
    db = get_session()
    try:
        user = db.query(UserProfile).filter(UserProfile.email == email).first()
        if not user:
            user = UserProfile(email=email); db.add(user)
        user.full_name = name; user.address_line1 = street; user.address_city = city
        user.address_state = state; user.address_zip = zip_code
        db.commit()
    except: pass
    finally: db.close()

# --- UPDATED FETCH FOR ADMIN ---
def fetch_all_drafts():
    """Returns all drafts as a list of dictionaries including CONTENT."""
    LetterDraft = get_model('letter_drafts')
    if not LetterDraft: return []
    db = get_session()
    try:
        results = db.query(LetterDraft).order_by(LetterDraft.created_at.desc()).all()
        data = []
        for r in results:
            data.append({
                "ID": r.id,
                "Email": r.user_email,
                "Tier": r.tier,
                "Status": r.status,
                "Date": r.created_at,
                "Price": r.price,
                "Content": r.transcription # Added this field
            })
        return data
    except Exception as e:
        print(f"Fetch Error: {e}")
        return []
    finally:
        db.close()