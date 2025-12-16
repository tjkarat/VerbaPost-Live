import streamlit as st
import sqlalchemy
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text, DateTime, func
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import contextmanager
import logging
import datetime
import uuid
import urllib.parse
import os

# --- CONFIGURATION ---
logger = logging.getLogger(__name__)

# Global variables for Lazy Loading (Prevents "Module Not Found" crashes)
_engine = None
_SessionLocal = None

def get_db_url():
    """
    Constructs the database URL.
    PRIORITY 1: st.secrets["supabase"] (Local & Streamlit Cloud)
    PRIORITY 2: os.environ (Cloud Run / Production)
    """
    sb_url = None
    sb_pass = None

    try:
        # --- PRIORITY 1: Check st.secrets (Your Setup) ---
        if "supabase" in st.secrets:
            sb_url = st.secrets["supabase"]["url"]
            # We use 'key' as the password, but safely encode it later
            sb_pass = st.secrets["supabase"]["key"]
            
        # --- PRIORITY 2: Check Environment Variables (Backup) ---
        elif "SUPABASE_URL" in os.environ:
            sb_url = os.environ.get("SUPABASE_URL")
            sb_pass = os.environ.get("SUPABASE_DB_PASSWORD") or os.environ.get("SUPABASE_KEY")

        # If we still don't have credentials, return None to handle gracefully
        if not sb_url or not sb_pass:
            return None

        # --- FIX: Construct the Safe URL ---
        
        # 1. Clean the Hostname (Remove https:// and trailing slashes)
        clean_host = sb_url.replace("https://", "").replace("/", "")
        
        # 2. Add 'db.' prefix if missing (Standard for Supabase direct connections)
        if not clean_host.startswith("db."):
             db_host = f"db.{clean_host}"
        else:
             db_host = clean_host

        # 3. URL Encode the Password (Crucial fix for your 'int' error)
        # This allows special characters in your API key to work as a password
        encoded_pass = urllib.parse.quote_plus(sb_pass)

        # 4. Return the formatted connection string
        return f"postgresql://postgres:{encoded_pass}@{db_host}:5432/postgres"
        
    except Exception as e:
        logger.error(f"Failed to construct DB URL: {e}")
        return None

def init_db():
    """Lazy initialization of the database engine."""
    global _engine, _SessionLocal
    
    if _engine is not None:
        return _engine, _SessionLocal
        
    url = get_db_url()
    if not url:
        # Stop here if secrets are missing, but don't crash the module import
        return None, None
        
    try:
        _engine = create_engine(url, pool_pre_ping=True)
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
        return _engine, _SessionLocal
    except Exception as e:
        logger.error(f"DB Init Error: {e}")
        return None, None

# Initialize Base (Must happen at module level)
Base = declarative_base()

# --- MODELS ---

class UserProfile(Base):
    __tablename__ = 'user_profiles'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Address / Physical Mail Data
    address_line1 = Column(String)
    address_city = Column(String)
    address_state = Column(String)
    country_code = Column(String, default="US")
    
    # Heirloom Specifics
    parent_name = Column(String)
    parent_phone = Column(String, index=True) 
    heirloom_status = Column(String, default="inactive")
    credits_remaining = Column(Integer, default=4)
    current_prompt = Column(Text, default="Tell me about your favorite childhood memory.")

class LetterDraft(Base):
    __tablename__ = 'letter_drafts'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_email = Column(String, index=True)
    content = Column(Text)
    status = Column(String, default="draft") # draft, sent
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# --- CORE UTILITIES ---

@contextmanager
def get_db_session():
    """Provides a transactional scope, initializing DB if needed."""
    engine, Session = init_db() # Lazy load here
    if not Session:
        raise ConnectionError("Database not initialized. Check secrets.")
        
    session = Session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def get_user_profile(email):
    """
    Returns user profile as a dictionary.
    """
    try:
        with get_db_session() as db:
            user = db.query(UserProfile).filter(UserProfile.email == email).first()
            if user:
                return {k: v for k, v in user.__dict__.items() if not k.startswith('_')}
            return None
    except Exception as e:
        logger.error(f"Get Profile Error: {e}")
        return None

def create_user(email, full_name):
    """Creates a new user if they don't exist."""
    try:
        with get_db_session() as db:
            user = UserProfile(email=email, full_name=full_name)
            db.add(user)
            db.commit()
            return True
    except Exception as e:
        logger.error(f"Create User Error: {e}")
        return False

# --- HEIRLOOM / DASHBOARD FUNCTIONS ---

def get_user_drafts(email):
    """Fetches all stories/drafts for a user."""
    try:
        with get_db_session() as db:
            drafts = db.query(LetterDraft).filter(
                LetterDraft.user_email == email
            ).order_by(LetterDraft.created_at.desc()).all()
            
            return [{k: v for k, v in d.__dict__.items() if not k.startswith('_')} for d in drafts]
    except Exception as e:
        logger.error(f"Get Drafts Error: {e}")
        return []

def update_draft_data(draft_id, content):
    """Updates the text of a story."""
    try:
        with get_db_session() as db:
            draft = db.query(LetterDraft).filter(LetterDraft.id == draft_id).first()
            if draft:
                draft.content = content
                return True
            return False
    except Exception as e:
        logger.error(f"Update Draft Error: {e}")
        return False

def decrement_user_credits(email):
    """
    Decreases user credits by 1. Returns (Success, New_Balance).
    """
    try:
        with get_db_session() as db:
            user = db.query(UserProfile).filter(UserProfile.email == email).first()
            if user and user.credits_remaining is not None and user.credits_remaining > 0:
                user.credits_remaining -= 1
                return True, user.credits_remaining
            return False, (user.credits_remaining if user else