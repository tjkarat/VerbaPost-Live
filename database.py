import streamlit as st
import sqlalchemy
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, Float, func, BigInteger
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
    CHECKS:
    1. os.environ (Production / Google Cloud Run) - PRIORITY
    2. st.secrets (Local / QA Streamlit Cloud) - FALLBACK
    """
    try:
        # --- FIX START: Check GCP Environment Variable First ---
        env_url = os.environ.get("DATABASE_URL")
        if env_url:
            return env_url
        # --- FIX END ---

        # Fallback to Streamlit Secrets (QA)
        if hasattr(st, "secrets"):
            if "DATABASE_URL" in st.secrets:
                return st.secrets["DATABASE_URL"]
            
            # Construct from Supabase parts if full URL isn't explicitly set
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
    address_zip = Column(String) 
    country_code = Column(String, default="US")
    
    # Heirloom Specifics
    parent_name = Column(String)
    parent_phone = Column(String, index=True) 
    heirloom_status = Column(String, default="inactive")
    credits_remaining = Column(Integer, default=1)
    current_prompt = Column(Text, default="Tell me about your favorite childhood memory.")

class LetterDraft(Base):
    """Used for Heirloom Stories"""
    __tablename__ = 'letter_drafts'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_email = Column(String, index=True)
    content = Column(Text)
    status = Column(String, default="draft")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    price = Column(Float, default=0.0)
    tier = Column(String, default="Heirloom") # Added to prevent Admin Console crash

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
    to_name = Column(String)
    to_city = Column(String)

class PromoCode(Base):
    """Refined to match your SQL exactly"""
    __tablename__ = 'promo_codes'
    code = Column(String, primary_key=True)
    active = Column(Boolean, default=True)        # From SQL schema
    is_active = Column(Boolean, default=True)     # Redundant but kept for safety
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    max_uses = Column(BigInteger)                 # From SQL schema
    discount_amount = Column(Float, default=0.0)
    current_uses = Column(Integer, default=0)     # Fixed AttributeError
    uses = Column(Integer, default=0)             # Fixed AttributeError

class PromoLog(Base):
    __tablename__ = 'promo_logs'
    id = Column(Integer, primary_key=True)
    code = Column(String, index=True)
    user_email = Column(String)
    # FIX: Explicitly use datetime.datetime.utcnow to avoid AttributeError
    used_at = Column(DateTime, default=datetime.datetime.utcnow)

class AuditEvent(Base):
    """Refined to match your SQL exactly"""
    __tablename__ = 'audit_events'
    # Changed ID to Integer/Serial to match SQL 'serial' type
    id = Column(Integer, primary_key=True, autoincrement=True) 
    timestamp = Column(DateTime, server_default=func.now()) 
    user_email = Column(String)          # Fixed AttributeError
    stripe_session_id = Column(String)   # From SQL schema
    event_type = Column(String)
    details = Column(Text)               # From SQL schema
    description = Column(Text)

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
            drafts = db.query(LetterDraft).filter(
                LetterDraft.user_email == email
            ).order_by(LetterDraft.created_at.desc()).all()
            return [{k: v for k, v in d.__dict__.items() if not k.startswith('_')} for d in drafts]
    except Exception as e:
        logger.error(f"Get Drafts Error: {e}")
        return []

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
                if tier is not None: draft.tier = tier
                
                # For Legacy Letters, we might update address fields
                if to_addr and hasattr(draft, 'to_name'):
                    draft.to_name = to_addr.get('name')
                    draft.to_city = to_addr.get('city')
                
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

# In database.py

def save_contact(user_email, contact_data):
    """
    Saves a new contact to the DB.
    Uses get_db_session() to avoid NameErrors.
    """
    try:
        with get_db_session() as session:
            # Create contact WITHOUT manually setting an ID (Let DB handle it)
            new_c = SavedContact(
                user_email=user_email,
                name=contact_data.get("name"),
                street=contact_data.get("street"),
                city=contact_data.get("city"),
                state=contact_data.get("state"),
                zip_code=contact_data.get("zip_code")
            )
            session.add(new_c)
            session.commit()
            return True
    except Exception as e:
        print(f"Save Contact Error: {e}")
        return False

# --- ADMIN FUNCTIONS ---

def get_all_promos():
    try:
        with get_db_session() as db:
            promos = db.query(PromoCode).all()
            return [{k: v for k, v in p.__dict__.items() if not k.startswith('_')} for p in promos]
    except Exception: return []

def create_promo_code(code, amount):
    try:
        with get_db_session() as db:
            # Initialize all fields to satisfy strict SQL constraints
            p = PromoCode(
                code=code, 
                discount_amount=amount, 
                active=True, 
                is_active=True, 
                current_uses=0, 
                uses=0
            )
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

def log_event(event_type, desc, user_email=None):
    try:
        with get_db_session() as db:
            log = AuditEvent(event_type=event_type, description=desc, user_email=user_email)
            db.add(log)
            db.commit()
    except Exception: pass

def get_all_orders():
    """Fetches both Legacy Letters and Heirloom Drafts for Admin Console"""
    try:
        with get_db_session() as db:
            # 1. Get Paid Legacy Letters
            legacy = db.query(Letter).filter(Letter.status != "Draft").order_by(Letter.created_at.desc()).all()
            # 2. Get Heirloom Drafts (that are ready/active)
            heirloom = db.query(LetterDraft).order_by(LetterDraft.created_at.desc()).limit(20).all()
            
            combined = []
            for o in legacy:
                combined.append({k: v for k, v in o.__dict__.items() if not k.startswith('_')})
            for h in heirloom:
                # Map Heirloom fields to what Admin expects
                d = {k: v for k, v in h.__dict__.items() if not k.startswith('_')}
                # Ensure tier exists if missing
                if 'tier' not in d or not d['tier']: d['tier'] = 'Heirloom' 
                combined.append(d)
                
            return combined
    except Exception as e:
        logger.error(f"Get Orders Error: {e}")
        return []