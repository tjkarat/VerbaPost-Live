import streamlit as st
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime

# --- GLOBAL SETUP (Define Models Once) ---
Base = declarative_base()

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

# --- ENGINE MANAGEMENT ---
@st.cache_resource
def get_engine():
    """Creates and caches the database engine."""
    if "DATABASE_URL" in st.secrets:
        # Fix postgres:// compatibility
        db_url = st.secrets["DATABASE_URL"].replace("postgres://", "postgresql://")
    else:
        print("⚠️ Warning: Using local SQLite.")
        db_url = "sqlite:///local_dev.db"

    try:
        engine = create_engine(db_url, pool_pre_ping=True)
        # Create tables if they don't exist
        Base.metadata.create_all(bind=engine)
        return engine
    except Exception as e:
        print(f"❌ DB Connection Error: {e}")
        return None

# --- SESSION MANAGEMENT ---
def get_session():
    """Creates a new database session."""
    engine = get_engine()
    if not engine: return None
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

# --- HELPER FUNCTIONS ---

def get_user_profile(email):
    db = get_session()
    if not db: return None
    try:
        return db.query(UserProfile).filter(UserProfile.email == email).first()
    except: return None
    finally: db.close()

def save_draft(email, text, tier, price, status="Draft", address_data=None):
    db = get_session()
    if not db: return None
    try:
        draft = LetterDraft(user_email=email, transcription=text, tier=tier, price=str(price), status=status)
        db.add(draft); db.commit(); db.refresh(draft)
        return draft.id
    except: db.rollback(); return None
    finally: db.close()

def update_user_profile(email, name, street, city, state, zip_code):
    db = get_session()
    if not db: return
    try:
        user = db.query(UserProfile).filter(UserProfile.email == email).first()
        if not user:
            user = UserProfile(email=email); db.add(user)
        user.full_name = name; user.address_line1 = street; user.address_city = city
        user.address_state = state; user.address_zip = zip_code
        db.commit()
    except: pass
    finally: db.close()

def fetch_all_drafts():
    """Returns all drafts as a list of dictionaries for the Admin Console."""
    db = get_session()
    if not db: return []
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
                "Content": r.transcription # Included for PDF generation
            })
        return data
    except: return []
    finally: db.close()