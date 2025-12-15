import streamlit as st
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.pool import QueuePool
import datetime
from contextlib import contextmanager
import logging
import secrets_manager

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- DATABASE MODELS ---
Base = declarative_base()

class UserProfile(Base):
    __tablename__ = "user_profiles"
    id = Column(String, primary_key=True, index=True) # Matches Supabase Auth ID
    email = Column(String, unique=True, index=True)
    full_name = Column(String, nullable=True)
    address_line1 = Column(String, nullable=True)
    address_city = Column(String, nullable=True)
    address_state = Column(String, nullable=True)
    address_zip = Column(String, nullable=True)
    country = Column(String, default="US")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class LetterDraft(Base):
    __tablename__ = "letter_drafts"
    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, index=True)
    content = Column(Text, nullable=True)
    status = Column(String, default="Draft")  # Draft, Paid, Sent
    tier = Column(String, default="Standard")
    price = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    # Metadata for tracking
    recipient_data = Column(Text, nullable=True) # JSON string
    sender_data = Column(Text, nullable=True)    # JSON string
    pdf_url = Column(String, nullable=True)
    tracking_number = Column(String, nullable=True)

class SavedContact(Base):
    __tablename__ = "saved_contacts"
    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, index=True)
    name = Column(String)
    street = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)
    country = Column(String, default="US")

class PromoCode(Base):
    __tablename__ = "promo_codes"
    code = Column(String, primary_key=True)
    discount_amount = Column(Float)
    max_uses = Column(Integer, default=100)
    current_uses = Column(Integer, default=0)
    active = Column(Boolean, default=True)

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String)
    user_email = Column(String, nullable=True)
    details = Column(Text)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

# --- ENGINE & SESSION ---
_engine = None

def get_engine():
    global _engine
    if _engine: return _engine
    
    # 1. Try Secrets Manager (Prod)
    db_url = secrets_manager.get_secret("SUPABASE_URL")
    if db_url and "supabase" in db_url:
        pass 
    
    # 2. Fallback to direct secrets.toml key (Dev)
    if not db_url:
        try:
            db_url = st.secrets["supabase"]["DATABASE_URL"]
        except:
            pass

    if not db_url:
        logger.warning("⚠️ No DATABASE_URL found. Using local SQLite.")
        db_url = "sqlite:///./local_dev.db"

    # Ensure robust connection for Cloud Run
    try:
        if "sqlite" in db_url:
            _engine = create_engine(db_url, connect_args={"check_same_thread": False})
        else:
            _engine = create_engine(
                db_url,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=1800,
                poolclass=QueuePool
            )
        Base.metadata.create_all(bind=_engine)
        return _engine
    except Exception as e:
        logger.error(f"DB Connection Error: {e}")
        return None

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())

@contextmanager
def get_db_session():
    """Safe session management."""
    engine = get_engine() # Ensure engine exists
    if not engine:
        raise Exception("Database Engine not initialized")
    
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

# --- CRUD OPERATIONS ---

# 1. USER PROFILES (FIXED: Added Missing Function)
def create_user_profile(profile_data):
    """Create or update a user profile. Sets ID correctly."""
    try:
        with get_db_session() as db:
            # Check if exists by email
            existing = db.query(UserProfile).filter(
                UserProfile.email == profile_data["email"]
            ).first()
            
            if existing:
                # Update existing
                for key, value in profile_data.items():
                    if hasattr(existing, key) and key != "id": # Don't overwrite ID
                        setattr(existing, key, value)
            else:
                # Create new
                new_profile = UserProfile(
                    id=profile_data.get("user_id"), # CRITICAL: Set ID from Auth
                    email=profile_data["email"],
                    full_name=profile_data.get("full_name", ""),
                    address_line1=profile_data.get("address_line1", ""),
                    address_city=profile_data.get("address_city", ""),
                    address_state=profile_data.get("address_state", ""),
                    address_zip=profile_data.get("address_zip", ""),
                    country=profile_data.get("country", "US")
                )
                db.add(new_profile)
            return True
    except Exception as e:
        logger.error(f"Create Profile Error: {e}")
        return False

def get_user_profile(email):
    try:
        with get_db_session() as db:
            return db.query(UserProfile).filter(UserProfile.email == email).first()
    except: return None

# 2. DRAFTS
def save_draft(user_email, content, tier, price):
    try:
        with get_db_session() as db:
            draft = LetterDraft(user_email=user_email, content=content, tier=tier, price=price)
            db.add(draft)
            db.flush() # Populate ID
            db.refresh(draft)
            return draft.id
    except Exception as e:
        logger.error(f"Save Draft Error: {e}")
        return None

def update_draft_data(draft_id, **kwargs):
    try:
        with get_db_session() as db:
            draft = db.query(LetterDraft).filter(LetterDraft.id == draft_id).first()
            if draft:
                for k, v in kwargs.items():
                    setattr(draft, k, v)
                return True
            return False
    except: return False

def get_draft(draft_id):
    try:
        with get_db_session() as db:
            return db.query(LetterDraft).filter(LetterDraft.id == draft_id).first()
    except: return None

# 3. CONTACTS (FIXED: Returns Dicts, Not Objects)
def save_contact(user_email, data):
    try:
        with get_db_session() as db:
            # Check duplicate
            exists = db.query(SavedContact).filter(
                SavedContact.user_email == user_email,
                SavedContact.name == data['name']
            ).first()
            if not exists:
                c = SavedContact(
                    user_email=user_email,
                    name=data.get('name'),
                    street=data.get('street'),
                    city=data.get('city'),
                    state=data.get('state'),
                    zip_code=data.get('zip'),
                    country=data.get('country', 'US')
                )
                db.add(c)
                return True
            return False
    except: return False

def get_contacts(user_email):
    """Returns a list of dictionaries to avoid SQLAlchemy object detachment errors."""
    if not user_email: return []
    try:
        with get_db_session() as db:
            contacts = db.query(SavedContact).filter(
                SavedContact.user_email == user_email
            ).order_by(SavedContact.name).all()
            
            # CRITICAL FIX: Convert to pure Python dicts
            results = []
            for c in contacts:
                results.append({
                    "name": c.name,
                    "street": c.street,
                    "city": c.city,
                    "state": c.state,
                    "zip_code": c.zip_code,
                    "country": c.country
                })
            return results
    except Exception as e:
        logger.error(f"Get Contacts Error: {e}")
        return []