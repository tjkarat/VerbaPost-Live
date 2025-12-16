import streamlit as st
import sqlalchemy
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, func
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import contextmanager
import logging
import uuid
import urllib.parse

# --- CONFIGURATION ---
logger = logging.getLogger(__name__)
Base = declarative_base()

# Global engine (Starts as None, loads only when needed)
_engine = None
_SessionLocal = None

def get_db_url():
    """
    Constructs the connection string for Streamlit Cloud.
    Target format: postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres
    """
    try:
        # 1. Grab secrets from Streamlit Cloud
        if "supabase" not in st.secrets:
            return None

        # 2. Get the parts
        sb_url = st.secrets["supabase"]["url"]
        
        # TRY to find a specific database password. 
        # If missing, fall back to the API key (sometimes works, but usually fails Auth).
        sb_pass = st.secrets["supabase"].get("db_password", st.secrets["supabase"].get("key"))

        if not sb_url or not sb_pass:
            return None

        # 3. Clean the Hostname
        # Turn "https://phqnppks...supabase.co" into "db.phqnppks...supabase.co"
        clean_host = sb_url.replace("https://", "").replace("/", "")
        if not clean_host.startswith("db."):
             db_host = f"db.{clean_host}"
        else:
             db_host = clean_host

        # 4. Escape the password (The fix for the original error)
        encoded_pass = urllib.parse.quote_plus(sb_pass)

        # 5. Build the string
        return f"postgresql://postgres:{encoded_pass}@{db_host}:5432/postgres"

    except Exception as e:
        logger.error(f"URL Construction Error: {e}")
        return None

def get_engine():
    """Lazy Loader: Only connects when we actually ask for data."""
    global _engine, _SessionLocal
    
    if _engine:
        return _engine
        
    url = get_db_url()
    if not url:
        raise ValueError("❌ Could not build DB URL. Check st.secrets['supabase'].")
        
    try:
        # Create engine
        _engine = create_engine(url, pool_pre_ping=True)
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
        return _engine
    except Exception as e:
        logger.error(f"Engine Creation Error: {e}")
        return None

# --- MODELS ---
class UserProfile(Base):
    __tablename__ = 'user_profiles'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    address_line1 = Column(String)
    address_city = Column(String)
    address_state = Column(String)
    country_code = Column(String, default="US")
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
    status = Column(String, default="draft")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# --- CORE UTILITIES ---

@contextmanager
def get_db_session():
    """Provides a transactional scope."""
    get_engine() # Ensure DB is ready
    if not _SessionLocal:
        raise ConnectionError("DB Session failed to initialize.")
        
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def get_user_profile(email):
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
    try:
        with get_db_session() as db:
            user = UserProfile(email=email, full_name=full_name)
            db.add(user)
            db.commit()
            return True
    except Exception as e:
        logger.error(f"Create User Error: {e}")
        return False

# --- HEIRLOOM FUNCTIONS ---

def get_user_drafts(email):
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
    if parent_phone:
        clean_phone = "".join(filter(str.isdigit, str(parent_phone)))
        if len(clean_phone) == 10:
            clean_phone = "+1" + clean_phone
        elif len(clean_phone) == 11 and clean_phone.startswith("1"):
            clean_phone = "+" + clean_phone
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