import streamlit as st
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import uuid

# --- 1. SETUP DATABASE CONNECTION ---
# We force it to look for the Postgres URL. 
# If missing, we print a loud error rather than silently failing to SQLite.

if "DATABASE_URL" in st.secrets:
    # SQLAlchemy requires 'postgresql://', but Supabase provides 'postgres://' sometimes.
    # We fix it to ensure compatibility.
    db_url = st.secrets["DATABASE_URL"].replace("postgres://", "postgresql://")
else:
    # FALLBACK (Only for local testing if no secrets, but warns user)
    print("⚠️ WARNING: No DATABASE_URL found. Using local SQLite (Data will be lost on reboot).")
    db_url = "sqlite:///local_dev.db"

try:
    engine = create_engine(db_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
except Exception as e:
    print(f"❌ Database Engine Error: {e}")
    st.error("System Error: Could not connect to Database.")
    # Create a dummy engine to prevent import crash, but app will fail later
    engine = create_engine("sqlite:///") 
    SessionLocal = sessionmaker(bind=engine)
    Base = declarative_base()

# --- 2. DEFINE TABLES (Models) ---

class UserProfile(Base):
    __tablename__ = "user_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    
    # Saved Addresses
    address_line1 = Column(String)
    address_city = Column(String)
    address_state = Column(String)
    address_zip = Column(String)
    
    created_at = Column(DateTime, default=datetime.utcnow)

class LetterDraft(Base):
    __tablename__ = "letter_drafts"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, index=True)
    
    # Content
    transcription = Column(Text)
    status = Column(String, default="Draft") # Draft, Paid, Sent
    
    # Meta
    tier = Column(String)
    price = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

# --- 3. AUTO-CREATE TABLES ---
# This line creates the tables in Supabase if they don't exist yet.
try:
    Base.metadata.create_all(bind=engine)
    print("✅ Database Tables Verified")
except Exception as e:
    print(f"❌ Error Creating Tables: {e}")

# --- 4. HELPER FUNCTIONS ---

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def save_draft(email, text, tier, price, status="Draft", address_data=None):
    """Saves or updates a draft letter."""
    db = SessionLocal()
    try:
        draft = LetterDraft(
            user_email=email,
            transcription=text,
            tier=tier,
            price=str(price),
            status=status
        )
        db.add(draft)
        db.commit()
        db.refresh(draft)
        return draft.id
    except Exception as e:
        print(f"Error saving draft: {e}")
        db.rollback()
        return None
    finally:
        db.close()

def update_user_profile(email, name, street, city, state, zip_code, lang="English"):
    """Updates user address profile"""
    db = SessionLocal()
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