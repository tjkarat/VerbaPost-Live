import os
import streamlit as st
import logging
import uuid
import urllib.parse
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, Float, DateTime, BigInteger, func
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import contextmanager
from datetime import datetime

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
        # Check GCP Environment Variable First
        env_url = os.environ.get("DATABASE_URL")
        if env_url: return env_url

        # Fallback to Streamlit Secrets
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
    if not url: return None, None
        
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
    # We map 'email' as the primary key for simplicity in lookups, 
    # though strict SQL might use a UUID 'id'
    email = Column(String, primary_key=True)
    full_name = Column(String)
    
    # Address Fields
    address_line1 = Column(String)
    address_line2 = Column(String)
    address_city = Column(String)
    address_state = Column(String)
    address_zip = Column(String)
    country = Column(String, default="US")
    
    # Heirloom Specific Fields
    parent_name = Column(String)
    parent_phone = Column(String)
    credits = Column(Integer, default=0) # This is the critical column for Subscriptions
    
    created_at = Column(DateTime, default=datetime.utcnow)

class LetterDraft(Base):
    """Used for Heirloom Stories"""
    __tablename__ = 'letter_drafts'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_email = Column(String)
    content = Column(Text)
    status = Column(String, default="Draft") # Draft, Paid, Sent
    tier = Column(String, default="Heirloom") 
    price = Column(Float, default=0.0)
    tracking_number = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class Letter(Base):
    """Used for Legacy/Store Orders (Paid Letters)"""
    __tablename__ = 'letters'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_email = Column(String, index=True)
    content = Column(Text)
    status = Column(String, default="Draft") 
    tier = Column(String, default="Standard")
    price = Column(Float, default=0.0)
    tracking_number = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    to_name = Column(String)
    to_city = Column(String)

class Contact(Base):
    __tablename__ = 'address_book'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_email = Column(String)
    name = Column(String)
    street = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)

class PromoCode(Base):
    __tablename__ = 'promo_codes'
    code = Column(String, primary_key=True)
    active = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True) # Redundant but safe
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    max_uses = Column(BigInteger)
    discount_amount = Column(Float, default=0.0)
    current_uses = Column(Integer, default=0)
    uses = Column(Integer, default=0)

class AuditEvent(Base):
    __tablename__ = 'audit_events'
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_email = Column(String)
    event_type = Column(String)
    details = Column(Text)
    description = Column(Text)

# ==========================================
# 🛠️ HELPER FUNCTIONS (Safe Dictionary Conversion)
# ==========================================

def to_dict(obj):
    """Converts SQLAlchemy object to dict to prevent DetachedInstanceError"""
    if not obj: return None
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}

# ==========================================
# 👤 USER & PROFILE FUNCTIONS
# ==========================================

def get_user_profile(email):
    try:
        with get_db_session() as session:
            profile = session.query(UserProfile).filter_by(email=email).first()
            if not profile:
                # Auto-create empty profile if missing
                profile = UserProfile(email=email, credits=0)
                session.add(profile)
                session.commit()
            return to_dict(profile)
    except Exception as e:
        logger.error(f"Get Profile Error: {e}")
        return {}

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

# ==========================================
# 🎙️ HEIRLOOM SPECIFIC FUNCTIONS (CRITICAL)
# ==========================================

def update_user_credits(email, new_credit_count):
    """
    Updates the credit balance for a user.
    Called by main.py after subscription payment.
    """
    try:
        with get_db_session() as session:
            profile = session.query(UserProfile).filter_by(email=email).first()
            if profile:
                profile.credits = new_credit_count
                session.commit()
                return True
            return False
    except Exception as e:
        logger.error(f"Credit Update Error: {e}")
        return False

def update_heirloom_settings(email, parent_name, parent_phone):
    """
    Updates parent details for the Heirloom service.
    Called by ui_heirloom.py settings form.
    """
    try:
        with get_db_session() as session:
            profile = session.query(UserProfile).filter_by(email=email).first()
            if profile:
                profile.parent_name = parent_name
                profile.parent_phone = parent_phone
                session.commit()
                return True
            return False
    except Exception as e:
        logger.error(f"Heirloom Settings Error: {e}")
        return False

def update_user_address(email, name, street, city, state, zip_code):
    """
    Updates the user's mailing address.
    Called by ui_heirloom.py settings form.
    """
    try:
        with get_db_session() as session:
            profile = session.query(UserProfile).filter_by(email=email).first()
            if profile:
                profile.full_name = name
                profile.address_line1 = street
                profile.address_city = city
                profile.address_state = state
                profile.address_zip = zip_code
                session.commit()
                return True
            return False
    except Exception as e:
        logger.error(f"Address Update Error: {e}")
        return False

# ==========================================
# 📝 DRAFT & LETTER FUNCTIONS
# ==========================================

def save_draft(email, content, tier="Standard", price=0.0):
    try:
        with get_db_session() as session:
            draft = LetterDraft(user_email=email, content=content, tier=tier, price=price, status="Draft")
            session.add(draft)
            session.commit()
            return draft.id
    except Exception as e:
        logger.error(f"Save Draft Error: {e}")
        return None

def get_user_drafts(email):
    try:
        with get_db_session() as session:
            drafts = session.query(LetterDraft).filter_by(user_email=email).order_by(LetterDraft.created_at.desc()).all()
            return [to_dict(d) for d in drafts]
    except Exception as e:
        logger.error(f"Get Drafts Error: {e}")
        return []

def update_draft_data(draft_id, **kwargs):
    """Universal update function for Drafts"""
    try:
        with get_db_session() as session:
            draft = session.query(LetterDraft).filter_by(id=draft_id).first()
            if draft:
                for key, val in kwargs.items():
                    if hasattr(draft, key):
                        setattr(draft, key, val)
                session.commit()
                return True
            return False
    except Exception as e:
        logger.error(f"Update Draft Error: {e}")
        return False

# ==========================================
# 📒 ADDRESS BOOK FUNCTIONS
# ==========================================

def get_contacts(email):
    try:
        with get_db_session() as session:
            contacts = session.query(Contact).filter_by(user_email=email).all()
            return [to_dict(c) for c in contacts]
    except Exception:
        return []

def save_contact(user_email, contact_data):
    try:
        with get_db_session() as session:
            new_c = Contact(
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
        logger.error(f"Save Contact Error: {e}")
        return False

# ==========================================
# 🛠️ ADMIN & PROMO FUNCTIONS
# ==========================================

def get_all_orders():
    """Fetches Drafts (Heirloom) and Letters (Store) for Admin Console"""
    try:
        with get_db_session() as session:
            # 1. Get Paid Letters (From Store)
            legacy = session.query(Letter).filter(Letter.status != "Draft").order_by(Letter.created_at.desc()).all()
            # 2. Get Heirloom Drafts
            heirloom = session.query(LetterDraft).order_by(LetterDraft.created_at.desc()).limit(20).all()
            
            combined = []
            for o in legacy:
                combined.append(to_dict(o))
            for h in heirloom:
                d = to_dict(h)
                if 'tier' not in d or not d['tier']: d['tier'] = 'Heirloom' 
                combined.append(d)
                
            return combined
    except Exception as e:
        logger.error(f"Get Orders Error: {e}")
        return []

def create_promo_code(code, amount):
    try:
        with get_db_session() as db:
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

def log_event(event_type, desc, user_email=None):
    try:
        with get_db_session() as db:
            log = AuditEvent(event_type=event_type, description=desc, user_email=user_email)
            db.add(log)
            db.commit()
    except Exception: pass