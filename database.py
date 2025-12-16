import streamlit as st
import sqlalchemy
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, func
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import contextmanager
import logging
import uuid
import urllib.parse
import os

# --- CONFIGURATION ---
logger = logging.getLogger(__name__)
Base = declarative_base()

# Global variables for Lazy Loading
_engine = None
_SessionLocal = None

def get_db_url():
    """
    Constructs the database URL.
    PRIORITY 1: st.secrets["DATABASE_URL"] (The specific line in your secrets)
    PRIORITY 2: st.secrets["supabase"] (Fallback construction)
    """
    try:
        # --- PRIORITY 1: The Explicit Variable (Your Setup) ---
        # This is the line: DATABASE_URL = "postgresql+psycopg2://..."
        if "DATABASE_URL" in st.secrets:
            return st.secrets["DATABASE_URL"]
            
        # --- PRIORITY 2: Manual Construction (Fallback) ---
        if "supabase" in st.secrets:
            sb_url = st.secrets["supabase"]["url"]
            sb_pass = st.secrets["supabase"].get("db_password", st.secrets["supabase"]["key"])
            
            clean_host = sb_url.replace("https://", "").replace("/", "")
            if not clean_host.startswith("db."):
                 db_host = f"db.{clean_host}"
            else:
                 db_host = clean_host

            encoded_pass = urllib.parse.quote_plus(sb_pass)
            return f"postgresql://postgres:{encoded_pass}@{db_host}:5432/postgres"

        return None
        
    except Exception as e:
        logger.error(f"Failed to find DB URL: {e}")
        return None

def init_db():
    """Lazy initialization of the database engine."""
    global _engine, _SessionLocal
    
    if _engine is not None:
        return _engine, _SessionLocal
        
    url = get_db_url()
    if not url:
        # Don't crash on import. Just return None so UI can show a nice error.
        return None, None
        
    try:
        _engine = create_engine(url, pool_pre_ping=True)
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
        return _engine, _SessionLocal
    except Exception as e:
        logger.error(f"DB Init Error: {e}")
        return None, None

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
    engine, Session = init_db()
    if not Session:
        raise ConnectionError("Database not initialized. Check DATABASE_URL in secrets.")
        
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