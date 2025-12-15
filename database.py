import streamlit as st
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.orm import sessionmaker, declarative_base
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
    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String, nullable=True)
    address_line1 = Column(String, nullable=True)
    address_city = Column(String, nullable=True)
    address_state = Column(String, nullable=True)
    address_zip = Column(String, nullable=True)
    country = Column(String, default="US")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "address_line1": self.address_line1,
            "address_city": self.address_city,
            "address_state": self.address_state,
            "address_zip": self.address_zip,
            "country": self.country
        }

class LetterDraft(Base):
    __tablename__ = "letter_drafts"
    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, index=True)
    content = Column(Text, nullable=True)
    status = Column(String, default="Draft")
    tier = Column(String, default="Standard")
    price = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    recipient_data = Column(Text, nullable=True) 
    sender_data = Column(Text, nullable=True)    
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
    discount_amount = Column(Float, default=0.0)
    max_uses = Column(Integer, default=100)
    current_uses = Column(Integer, default=0)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class PromoLog(Base):
    __tablename__ = "promo_logs"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, index=True)
    user_email = Column(String)
    used_at = Column(DateTime, default=datetime.datetime.utcnow)

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
    
    db_url = None
    if secrets_manager:
        db_url = secrets_manager.get_secret("DATABASE_URL")
    
    if not db_url and "supabase" in st.secrets:
        db_url = st.secrets["supabase"].get("db_url")

    # Fallback to local
    if not db_url:
        logger.warning("⚠️ No DATABASE_URL found. Using local SQLite.")
        db_url = "sqlite:///./local_dev.db"
    
    # Fix Dialect
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

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
                poolclass=QueuePool,  # <--- CRITICAL FIX: Added comma here
                connect_args={'options': '-csearch_path=public'}
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
    engine = get_engine() 
    if not engine:
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
    
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

def create_user_profile(profile_data):
    try:
        with get_db_session() as db:
            existing = db.query(UserProfile).filter(UserProfile.email == profile_data["email"]).first()
            if existing:
                for key, value in profile_data.items():
                    if hasattr(existing, key) and key != "id":
                        setattr(existing, key, value)
            else:
                new_profile = UserProfile(
                    id=profile_data.get("user_id"),
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
    """Fetches profile and converts to DICT."""
    try:
        with get_db_session() as db:
            profile = db.query(UserProfile).filter(UserProfile.email == email).first()
            if profile:
                return profile.to_dict()
            return None
    except Exception as e:
        logger.error(f"Get Profile Error: {e}")
        return None

def save_draft(user_email, content, tier, price):
    try:
        with get_db_session() as db:
            draft = LetterDraft(user_email=user_email, content=content, tier=tier, price=price)
            db.add(draft)
            db.flush()
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

def save_contact(user_email, data):
    try:
        with get_db_session() as db:
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
    if not user_email: return []
    try:
        with get_db_session() as db:
            contacts = db.query(SavedContact).filter(SavedContact.user_email == user_email).order_by(SavedContact.name).all()
            return [{
                "name": c.name, "street": c.street, "city": c.city, 
                "state": c.state, "zip_code": c.zip_code, "country": c.country
            } for c in contacts]
    except Exception as e:
        logger.error(f"Get Contacts Error: {e}")
        return []