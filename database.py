import streamlit as st
import sqlalchemy
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, Float, func
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import contextmanager
import logging
import uuid
import urllib.parse
import os
import datetime

# --- CONFIGURATION ---
logger = logging.getLogger(__name__)
Base = declarative_base()

# Global variables for Lazy Loading
_engine = None
_SessionLocal = None

def get_db_url():
    """
    Constructs the database URL safely.
    """
    try:
        # PRIORITY 1: Explicit 'DATABASE_URL' in secrets
        if "DATABASE_URL" in st.secrets:
            return st.secrets["DATABASE_URL"]
            
        # PRIORITY 2: Construct from 'supabase' section
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
        return None, None
        
    try:
        _engine = create_engine(url, pool_pre_ping=True)
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
        return _engine, _SessionLocal
    except Exception as e:
        logger.error(f"DB Init Error: {e}")
        return None, None

# --- CORE UTILITIES ---

@contextmanager
def get_db_session():
    """Provides a transactional scope."""
    engine, Session = init_db()
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

# ==========================================
# 🏛️ MODELS (Unified Schema)
# ==========================================

class UserProfile(Base):
    __tablename__ = 'user_profiles'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Address
    address_line1 = Column(String)
    address_city = Column(String)
    address_state = Column(String)
    address_zip = Column(String) # Restored for legacy compatibility
    country_code = Column(String, default="US")
    
    # Heirloom
    parent_name = Column(String)
    parent_phone = Column(String, index=True) 
    heirloom_status = Column(String, default="inactive")
    credits_remaining = Column(Integer, default=4)
    current_prompt = Column(Text, default="Tell me about your favorite childhood memory.")

class LetterDraft(Base):
    """Used for Heirloom Stories"""
    __tablename__ = 'letter_drafts'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_email = Column(String, index=True)
    content = Column(Text)
    status = Column(String, default="draft")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    price = Column(Float, default=0.0) # Added for compatibility

class Letter(Base):
    """Used for Legacy/Store Orders (Paid Letters)"""
    __tablename__ = 'letters'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_email = Column(String, index=True)
    content = Column(Text)
    status = Column(String, default="Draft") # Draft, Paid, Sent
    tier = Column(String, default="Standard")
    price = Column(Float, default=0.0)
    tracking_number = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # JSON storage for addresses if needed, or simple text fields
    to_name = Column(String)
    to_city = Column(String)

class PromoCode(Base):
    """Restored for Admin Console"""
    __tablename__ = 'promo_codes'
    code = Column(String, primary_key=True)
    discount_amount = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    uses = Column(Integer, default=0)

class AuditEvent(Base):
    """Restored for Admin Console Logs"""
    __tablename__ = 'audit_events'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type = Column(String)
    description = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class Contact(Base):
    """Restored for Address Book"""
    __tablename__ = 'saved_contacts'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_email = Column(String, index=True)
    name = Column(String)
    street = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)


# ==========================================
# 🛠️ FUNCTIONS
# ==========================================

# --- USER FUNCTIONS ---
def get_user_profile(email):
    try:
        with get_db_session() as db:
            user = db.query(UserProfile).filter(UserProfile.email == email).first()
            if user:
                return {k: v for k, v in user.__dict__.items() if not k.startswith('_')}
            return None
    except Exception: return None

def create_user(email, full_name):
    try:
        with get_db_session() as db:
            user = UserProfile(email=email, full_name=full_name)
            db.add(user)
            db.commit()
            return True
    except Exception: return False

def get_all_users():
    """For Admin Console"""
    try:
        with get_db_session() as db:
            users = db.query(UserProfile).all()
            return [{k: v for k, v in u.__dict__.items() if not k.startswith('_')} for u in users]
    except Exception: return []

# --- HEIRLOOM FUNCTIONS ---
def get_user_drafts(email):
    try:
        with get_db_session() as db:
            drafts = db.query(LetterDraft).filter(LetterDraft.user_email == email).order_by(LetterDraft.created_at.desc()).all()
            return [{k: v for k, v in d.__dict__.items() if not k.startswith('_')} for d in drafts]
    except Exception: return []

def update_draft_data(draft_id, content=None, status=None, price=None, to_addr=None, from_addr=None, tier=None):
    """Universal update function for both Drafts and Letters"""
    try:
        with get_db_session() as db:
            # Try finding in LetterDraft first
            draft = db.query(LetterDraft).filter(LetterDraft.id == draft_id).first()
            if not draft:
                # Fallback to Legacy Letter table
                draft = db.query(Letter).filter(Letter.id == draft_id).first()
            
            if draft:
                if content is not None: draft.content = content
                if status is not None: draft.status = status
                if price is not None: draft.price = price
                # Add other fields as needed
                return True
            return False
    except Exception: return False

def decrement_user_credits(email):
    try:
        with get_db_session() as db:
            user = db.query(UserProfile).filter(UserProfile.email == email).first()
            if user and user.credits_remaining > 0:
                user.credits_remaining -= 1
                return True, user.credits_remaining
            return False, 0
    except Exception: return False, 0

def update_user_prompt(email, new_prompt):
    try:
        with get_db_session() as db:
            user = db.query(UserProfile).filter(UserProfile.email == email).first()
            if user:
                user.current_prompt = new_prompt
                return True
            return False
    except Exception: return False

def update_heirloom_profile(email, parent_name, parent_phone):
    clean_phone = None
    if parent_phone:
        clean_phone = "".join(filter(str.isdigit, str(parent_phone)))
        if len(clean_phone) == 10: clean_phone = "+1" + clean_phone
        elif len(clean_phone) == 11 and clean_phone.startswith("1"): clean_phone = "+" + clean_phone

    try:
        with get_db_session() as db:
            user = db.query(UserProfile).filter(UserProfile.email == email).first()
            if user:
                user.parent_name = parent_name
                user.parent_phone = clean_phone
                user.heirloom_status = "active"
                return True
            return False
    except Exception: return False

# --- LEGACY / STORE FUNCTIONS ---
def save_draft(email, content, tier, price):
    """Creates a legacy 'Letter' for store purchase"""
    try:
        with get_db_session() as db:
            letter = Letter(user_email=email, content=content, tier=tier, price=price)
            db.add(letter)
            db.commit()
            return letter.id
    except Exception: return None

def get_contacts(email):
    try:
        with get_db_session() as db:
            contacts = db.query(Contact).filter(Contact.user_email == email).all()
            return [{k: v for k, v in c.__dict__.items() if not k.startswith('_')} for c in contacts]
    except Exception: return []

# --- ADMIN FUNCTIONS (Restored) ---
def get_all_promos():
    try:
        with get_db_session() as db:
            promos = db.query(PromoCode).all()
            return [{k: v for k, v in p.__dict__.items() if not k.startswith('_')} for p in promos]
    except Exception: return []

def create_promo_code(code, amount):
    try:
        with get_db_session() as db:
            p = PromoCode(code=code, discount_amount=amount)
            db.add(p)
            db.commit()
            return True
    except Exception: return False

def get_system_logs(limit=50):
    try:
        with get_db_session() as db:
            logs = db.query(AuditEvent).order_by(AuditEvent.timestamp.desc()).limit(limit).all()
            return [{k: v for k, v in l.__dict__.items() if not k.startswith('_')} for l in logs]
    except Exception: return []

def log_event(event_type, desc):
    try:
        with get_db_session() as db:
            log = AuditEvent(event_type=event_type, description=desc)
            db.add(log)
            db.commit()
    except Exception: pass

def get_all_orders():
    """Fetches paid letters for Admin Orders tab"""
    try:
        with get_db_session() as db:
            # We look for letters that are NOT drafts
            orders = db.query(Letter).filter(Letter.status != "Draft").order_by(Letter.created_at.desc()).all()
            return [{k: v for k, v in o.__dict__.items() if not k.startswith('_')} for o in orders]
    except Exception: return []