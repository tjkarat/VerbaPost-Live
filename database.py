import os
import streamlit as st
import logging
import urllib.parse
import json
import uuid
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
    """Retrieves the database URL from secrets or environment variables."""
    if not secrets_manager:
        return os.environ.get("DATABASE_URL")
    try:
        url = secrets_manager.get_secret("DATABASE_URL")
        if url: return url
        
        # Fallback to granular Supabase secrets
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
    """Initializes the SQLAlchemy engine and creates tables."""
    global _engine, _SessionLocal
    if _engine is not None: return _engine, _SessionLocal
    url = get_db_url()
    if not url: return None, None
    try:
        _engine = create_engine(url, pool_pre_ping=True)
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
        # Ensure all tables are created
        Base.metadata.create_all(_engine)
        return _engine, _SessionLocal
    except Exception as e:
        logger.error(f"DB Init Error: {e}")
        return None, None

@contextmanager
def get_db_session():
    """Context manager for handling database sessions."""
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
    """Converts a SQLAlchemy object to a dictionary."""
    if not obj: return None
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}

# ==========================================
# 🏛️ LEGACY MODELS (PRESERVED)
# ==========================================

class UserProfile(Base):
    """B2C Retail User Profiles."""
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
    role = Column(String, default="user")

class LetterDraft(Base):
    """
    Standard Retail Letter Store Drafts. 
    Restored recipient_data and sender_data to fix Admin Console crash.
    """
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
    recipient_data = Column(Text) # RESTORED
    sender_data = Column(Text)    # RESTORED

class AuditEvent(Base):
    """Internal system logs."""
    __tablename__ = 'audit_events'
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_email = Column(String)
    event_type = Column(String)
    details = Column(Text)
    description = Column(Text)
    stripe_session_id = Column(String)

class PromoCode(Base):
    """Discount codes."""
    __tablename__ = 'promo_codes'
    code = Column(String, primary_key=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    max_uses = Column(BigInteger)
    discount_amount = Column(Float, default=0.0)
    uses = Column(Integer, default=0)

# ==========================================
# 🚀 NEW B2B MODELS (HYBRID READY)
# ==========================================

class Advisor(Base):
    """Financial Advisor Firm profiles."""
    __tablename__ = 'advisors'
    email = Column(String, primary_key=True)
    firm_name = Column(String, default="New Firm")
    full_name = Column(String)
    address = Column(Text) 
    created_at = Column(DateTime, default=datetime.utcnow)

class Client(Base):
    """The Advisor's CRM Table."""
    __tablename__ = 'clients'
    id = Column(Integer, primary_key=True, autoincrement=True)
    advisor_email = Column(String, ForeignKey('advisors.email'))
    name = Column(String, nullable=False)
    phone = Column(String)
    heir_name = Column(String)
    status = Column(String, default='Active')
    created_at = Column(DateTime, default=datetime.utcnow)

class Project(Base):
    """The unique Legacy Gift instance."""
    __tablename__ = 'projects'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    advisor_email = Column(String, ForeignKey('advisors.email'), nullable=False)
    client_id = Column(Integer, ForeignKey('clients.id'))
    heir_name = Column(String)
    heir_address_json = Column(Text, default="{}")
    strategic_prompt = Column(Text)
    content = Column(Text) 
    audio_ref = Column(Text) 
    status = Column(String, default='Authorized') 
    scheduled_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# ==========================================
# 🛠️ HELPER FUNCTIONS (RESTORED)
# ==========================================

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

def get_all_users():
    try:
        with get_db_session() as session:
            users = session.query(UserProfile).all()
            return [to_dict(u) for u in users]
    except Exception: return []

def update_user_role(email, role):
    try:
        with get_db_session() as session:
            user = session.query(UserProfile).filter_by(email=email).first()
            if user:
                user.role = role
                session.commit()
                return True
            return False
    except Exception: return False

def get_all_orders():
    try:
        with get_db_session() as session:
            drafts = session.query(LetterDraft).order_by(LetterDraft.created_at.desc()).limit(100).all()
            return [to_dict(d) for d in drafts]
    except Exception: return []

def get_all_promos():
    try:
        with get_db_session() as session:
            promos = session.query(PromoCode).all()
            return [to_dict(p) for p in promos]
    except Exception: return []

def create_promo_code(code, amount):
    try:
        with get_db_session() as session:
            new_p = PromoCode(code=code, discount_amount=amount)
            session.add(new_p)
            session.commit()
            return True
    except Exception: return False

# ==========================================
# 🛠️ B2B HELPER FUNCTIONS (HYBRID MODEL)
# ==========================================

def get_or_create_advisor(email):
    try:
        with get_db_session() as session:
            adv = session.query(Advisor).filter_by(email=email).first()
            if not adv:
                adv = Advisor(email=email, firm_name="Unregistered Firm")
                session.add(adv)
                session.commit()
            return to_dict(adv)
    except Exception: return {}

def get_clients(advisor_email):
    """RESTORED: Fetches clients for the Advisor Roster."""
    try:
        with get_db_session() as session:
            res = session.query(Client).filter_by(advisor_email=advisor_email).order_by(Client.created_at.desc()).all()
            return [to_dict(r) for r in res]
    except Exception: return []

def create_hybrid_project(advisor_email, parent_name, parent_phone, heir_name, prompt):
    try:
        with get_db_session() as session:
            client = session.query(Client).filter_by(advisor_email=advisor_email, phone=parent_phone).first()
            if not client:
                client = Client(advisor_email=advisor_email, name=parent_name, phone=parent_phone, heir_name=heir_name)
                session.add(client)
                session.flush() 
            
            new_proj = Project(
                advisor_email=advisor_email,
                client_id=client.id,
                heir_name=heir_name,
                strategic_prompt=prompt,
                status="Authorized"
            )
            session.add(new_proj)
            session.commit()
            return new_proj.id
    except Exception: return None

def get_pending_approvals(advisor_email):
    """RESTORED: Fetches projects requiring Advisor review."""
    try:
        with get_db_session() as session:
            # We map the Project back to Parent data for the UI
            projs = session.query(Project).filter_by(advisor_email=advisor_email, status="Recorded").all()
            results = []
            for p in projs:
                client = session.query(Client).filter_by(id=p.client_id).first()
                d = to_dict(p)
                d['parent_name'] = client.name if client else "Unknown"
                results.append(d)
            return results
    except Exception: return []

def get_project_by_id(project_id):
    try:
        with get_db_session() as session:
            proj = session.query(Project).filter_by(id=project_id).first()
            if not proj: return None
            adv = session.query(Advisor).filter_by(email=proj.advisor_email).first()
            client = session.query(Client).filter_by(id=proj.client_id).first()
            data = to_dict(proj)
            data['firm_name'] = adv.firm_name if adv else "VerbaPost Partner"
            data['parent_name'] = client.name if client else "Client"
            return data
    except Exception: return None

def update_project_details(project_id, address=None, scheduled_time=None, status=None, content=None):
    try:
        with get_db_session() as session:
            proj = session.query(Project).filter_by(id=project_id).first()
            if proj:
                if address: proj.heir_address_json = json.dumps(address)
                if scheduled_time: proj.scheduled_time = scheduled_time
                if status: proj.status = status
                if content: proj.content = content
                session.commit()
                return True
            return False
    except Exception: return False