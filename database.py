import os
import streamlit as st
import logging
import urllib.parse
import json
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, Float, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from contextlib import contextmanager
from datetime import datetime

# --- IMPORT SECRETS ---
try: import secrets_manager
except ImportError: secrets_manager = None

logger = logging.getLogger(__name__)
Base = declarative_base()

# Global variables for Lazy Loading
_engine = None
_SessionLocal = None

def get_db_url():
    if not secrets_manager:
        return os.environ.get("DATABASE_URL")
    try:
        url = secrets_manager.get_secret("DATABASE_URL")
        if url: return url
        
        # Fallback to granular secrets
        sb_url = secrets_manager.get_secret("supabase.url")
        sb_key = secrets_manager.get_secret("supabase.key")
        sb_pass = secrets_manager.get_secret("supabase.db_password")
        
        if sb_url and sb_pass:
            encoded_pass = urllib.parse.quote_plus(sb_pass)
            clean_host = sb_url.replace("https://", "").replace("/", "")
            return f"postgresql://postgres:{encoded_pass}@{clean_host}:5432/postgres"
            
        return None
    except Exception as e:
        logger.error(f"Failed to find DB URL: {e}")
        return None

def init_db():
    global _engine, _SessionLocal
    if _engine is not None: return _engine, _SessionLocal
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
    engine, Session = init_db()
    if not Session: raise ConnectionError("Database not initialized.")
    session = Session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def to_dict(obj):
    if not obj: return None
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}

# ==========================================
# 🏛️ EXISTING MODELS (PRESERVED)
# ==========================================

class UserProfile(Base):
    __tablename__ = 'user_profiles'
    email = Column(String, primary_key=True)
    full_name = Column(String)
    address_line1 = Column(String)
    address_line2 = Column(String)
    address_city = Column(String)
    address_state = Column(String)
    address_zip = Column(String)
    country = Column(String, default="US")
    timezone = Column(String, default="US/Central") 
    parent_name = Column(String)
    parent_phone = Column(String)
    credits = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_call_date = Column(DateTime, nullable=True)
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    subscription_end_date = Column(DateTime, nullable=True)
    is_partner = Column(Boolean, default=False)

class LetterDraft(Base):
    __tablename__ = 'letter_drafts'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_email = Column(String)
    content = Column(Text)
    status = Column(String, default="Draft")
    tier = Column(String, default="Standard") 
    price = Column(Float, default=0.0)
    tracking_number = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    to_addr = Column(Text)
    from_addr = Column(Text)
    recipient_data = Column(Text) 
    sender_data = Column(Text)

class AuditEvent(Base):
    __tablename__ = 'audit_events'
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_email = Column(String)
    event_type = Column(String)
    details = Column(Text)
    description = Column(Text)
    stripe_session_id = Column(String)

class PromoCode(Base):
    __tablename__ = 'promo_codes'
    code = Column(String, primary_key=True)
    active = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True))
    max_uses = Column(BigInteger)
    discount_amount = Column(Float, default=0.0)
    current_uses = Column(Integer, default=0)
    uses = Column(Integer, default=0)

# ==========================================
# 🚀 NEW B2B MODELS (ADDITIVE)
# ==========================================

class Advisor(Base):
    __tablename__ = 'advisors'
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False)
    firm_name = Column(String)
    full_name = Column(String)
    stripe_customer_id = Column(String)
    subscription_status = Column(String, default='active')
    credits = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Client(Base):
    __tablename__ = 'clients'
    id = Column(Integer, primary_key=True, autoincrement=True)
    advisor_email = Column(String, ForeignKey('advisors.email'))
    name = Column(String, nullable=False)
    phone = Column(String)
    email = Column(String)
    address_json = Column(Text)
    status = Column(String, default='Active')
    created_at = Column(DateTime, default=datetime.utcnow)

class Project(Base):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True, autoincrement=True)
    advisor_email = Column(String, nullable=False)
    client_id = Column(Integer, ForeignKey('clients.id'))
    project_type = Column(String, default='Retainer_Letter')
    status = Column(String, default='Draft')
    content = Column(Text)
    audio_ref = Column(Text)
    tracking_number = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

# ==========================================
# 🛠️ HELPER FUNCTIONS
# ==========================================

# --- PRESERVED FOR UI_LOGIN ---
def get_user_profile(email):
    try:
        with get_db_session() as session:
            profile = session.query(UserProfile).filter_by(email=email).first()
            if not profile:
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

# --- PRESERVED FOR UI_ADMIN ---
def get_all_orders():
    # Only fetches LetterDrafts for now to keep it simple
    try:
        with get_db_session() as session:
            drafts = session.query(LetterDraft).order_by(LetterDraft.created_at.desc()).limit(100).all()
            return [to_dict(d) for d in drafts]
    except Exception: return []

def save_audit_log(log_entry):
    try:
        with get_db_session() as session:
            # Simple filter for allowed keys
            valid_keys = {'user_email', 'event_type', 'details', 'description', 'stripe_session_id'}
            filtered = {k: v for k, v in log_entry.items() if k in valid_keys}
            log = AuditEvent(**filtered)
            session.add(log)
            session.commit()
            return True
    except Exception: return False

def get_audit_logs(limit=100):
    try:
        with get_db_session() as session:
            logs = session.query(AuditEvent).order_by(AuditEvent.timestamp.desc()).limit(limit).all()
            return [to_dict(l) for l in logs]
    except Exception: return []

# --- NEW B2B HELPERS ---
def get_or_create_advisor(email):
    try:
        with get_db_session() as session:
            advisor = session.query(Advisor).filter_by(email=email).first()
            if not advisor:
                # Migrate name from old profile if exists
                legacy = session.query(UserProfile).filter_by(email=email).first()
                full_name = legacy.full_name if legacy else ""
                
                advisor = Advisor(email=email, full_name=full_name)
                session.add(advisor)
                session.commit()
            return to_dict(advisor)
    except Exception as e:
        logger.error(f"Advisor Get Error: {e}")
        return None

def get_clients(advisor_email):
    try:
        with get_db_session() as session:
            clients = session.query(Client).filter_by(advisor_email=advisor_email).order_by(Client.created_at.desc()).all()
            return [to_dict(c) for c in clients]
    except Exception as e:
        logger.error(f"Get Clients Error: {e}")
        return []

def add_client(advisor_email, name, phone, address_dict=None):
    try:
        addr_str = json.dumps(address_dict) if address_dict else "{}"
        with get_db_session() as session:
            new_client = Client(
                advisor_email=advisor_email,
                name=name,
                phone=phone,
                address_json=addr_str
            )
            session.add(new_client)
            session.commit()
            return True
    except Exception as e:
        logger.error(f"Add Client Error: {e}")
        return False
    # ... (Keep all existing code)

# ==========================================
# 🛠️ PROJECT HELPERS (B2B)
# ==========================================

def create_project(advisor_email, client_id, project_type="Heirloom_Interview"):
    try:
        with get_db_session() as session:
            # check for active projects to prevent duplicates
            existing = session.query(Project).filter_by(
                client_id=client_id, 
                status='Recording'
            ).first()
            
            if existing:
                return existing.id

            new_proj = Project(
                advisor_email=advisor_email,
                client_id=client_id,
                project_type=project_type,
                status='Recording'
            )
            session.add(new_proj)
            session.commit()
            return new_proj.id
    except Exception as e:
        logger.error(f"Create Project Error: {e}")
        return None

def update_project_audio(project_id, audio_ref, transcript):
    """Called by AI Engine after the call is done"""
    try:
        with get_db_session() as session:
            proj = session.query(Project).filter_by(id=project_id).first()
            if proj:
                proj.audio_ref = audio_ref
                proj.content = transcript
                proj.status = "Advisor_Review" # Move to approval queue
                session.commit()
                return True
            return False
    except Exception as e:
        logger.error(f"Update Project Error: {e}")
        return False