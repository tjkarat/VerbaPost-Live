import streamlit as st
import sqlalchemy
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text, DateTime, func
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import contextmanager
import logging
import datetime
import uuid
import urllib.parse  # Added for safe URL construction

# --- CONFIGURATION ---
logger = logging.getLogger(__name__)

def get_db_url():
    """
    Constructs a valid SQLAlchemy connection string safely.
    Format: postgresql://user:password@host:port/database
    """
    try:
        # 1. Get Secrets
        # We try to find the URL and Key/Password in st.secrets
        if "supabase" in st.secrets:
            sb_url = st.secrets["supabase"]["url"]
            # Try to use a specific DB password first, otherwise fall back to the API key
            # (Note: Using API key as DB password only works if Supabase is configured for it, 
            # usually you need the specific postgres password)
            sb_pass = st.secrets["supabase"].get("db_password", st.secrets["supabase"]["key"])
        else:
            # Fallback for environment variables (Cloud Run)
            import os
            sb_url = os.environ.get("SUPABASE_URL", "")
            sb_pass = os.environ.get("SUPABASE_DB_PASSWORD", os.environ.get("SUPABASE_KEY", ""))

        if not sb_url or not sb_pass:
            return "postgresql://" # Return dummy to prevent immediate import crash

        # 2. Extract Hostname (e.g. 'xyz.supabase.co')
        # We strip https:// and trailing slashes to get just the domain
        clean_host = sb_url.replace("https://", "").replace("/", "")
        
        # Supabase direct DB connections usually require the 'db.' prefix
        # e.g. db.phqnppksrypylqpzmlxv.supabase.co
        if not clean_host.startswith("db."):
             db_host = f"db.{clean_host}"
        else:
             db_host = clean_host

        # 3. URL Encode the password (crucial if it has symbols like @, :, /)
        encoded_pass = urllib.parse.quote_plus(sb_pass)

        # 4. Construct the Final URL
        # Standard Supabase port is 5432, user is 'postgres', db is 'postgres'
        return f"postgresql://postgres:{encoded_pass}@{db_host}:5432/postgres"
        
    except Exception as e:
        logger.error(f"Failed to construct DB URL: {e}")
        return "postgresql://" 

# Initialize Engine
DB_URL = get_db_url()
engine = create_engine(DB_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
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
    
    # Heirloom Specifics (Phase 1 & 2)
    parent_name = Column(String)
    parent_phone = Column(String, index=True) # Indexed for fast lookup by Twilio
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
    """Provides a transactional scope around a series of operations."""
    session = SessionLocal()
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
    Returns user profile as a dictionary to be safe for Streamlit.
    """
    try:
        with get_db_session() as db:
            user = db.query(UserProfile).filter(UserProfile.email == email).first()
            if user:
                # Convert SQLAlchemy object to standard dict
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
            return False, (user.credits_remaining if user else 0)
    except Exception as e:
        logger.error(f"Credit Error: {e}")
        return False, 0

def update_user_prompt(email, new_prompt):
    """
    Updates the 'Brain' topic for the next call.
    """
    try:
        with get_db_session() as db:
            user = db.query(UserProfile).filter(UserProfile.email == email).first()
            if user:
                user.current_prompt = new_prompt
                return True
            return False
    except Exception as e:
        logger.error(f"Update Prompt Error: {e}")
        return False

def update_heirloom_profile(email, parent_name, parent_phone):
    """
    Updates parent details AND fixes phone formatting for Twilio.
    Example: '615-555-0100' -> '+16155550100'
    """
    # 1. Clean the phone (digits only)
    if parent_phone:
        clean_phone = "".join(filter(str.isdigit, str(parent_phone)))
        
        # 2. Add +1 (US Country Code) if missing
        if len(clean_phone) == 10:
            clean_phone = "+1" + clean_phone
        elif len(clean_phone) == 11 and clean_phone.startswith("1"):
            clean_phone = "+" + clean_phone
        # Else: leave it alone (could be international or already formatted)
    else:
        clean_phone = None

    try:
        with get_db_session() as db:
            user = db.query(UserProfile).filter(UserProfile.email == email).first()
            if user:
                user.parent_name = parent_name
                user.parent_phone = clean_phone
                user.heirloom_status = "active"
                return True
            return False
    except Exception as e:
        logger.error(f"Update Heirloom Profile Error: {e}")
        return False