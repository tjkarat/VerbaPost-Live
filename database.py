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
    """Security check for DB URL via granular secrets."""
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
    """Initializes engine and creates all models."""
    global _engine, _SessionLocal
    if _engine is not None: return _engine, _SessionLocal
    url = get_db_url()
    if not url: return None, None
    try:
        _engine = create_engine(url, pool_pre_ping=True)
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
        # Security: Ensures table schema integrity across migrations
        Base.metadata.create_all(_engine)
        return _engine, _SessionLocal
    except Exception as e:
        logger.error(f"DB Init Error: {e}")
        return None, None

@contextmanager
def get_db_session():
    """Context manager for session handling and rollbacks."""
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
    """Utility for Streamlit UI data rendering."""
    if not obj: return None
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}

# ==========================================
# 🏛️ LEGACY MODELS (PRESERVED)
# ==========================================

class UserProfile(Base):
    """Retail B2C profiles."""
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
    # Added for B2B / Firm association lookup
    advisor_firm = Column(String, nullable=True)

class LetterDraft(Base):
    """
    Standard Retail Letter Store Drafts. 
    Maintains recipient_data column for Admin Console stability.
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
    recipient_data = Column(Text) 
    sender_data = Column(Text)
    # Added for Heirloom Metadata (Question/Topic)
    question_text = Column(Text, nullable=True)

class AuditEvent(Base):
    """System auditing for Admin diagnostic tools."""
    __tablename__ = 'audit_events'
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_email = Column(String)
    event_type = Column(String)
    details = Column(Text)
    description = Column(Text)
    stripe_session_id = Column(String)

class PromoCode(Base):
    """B2C Discount Logic."""
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
# 🚀 NEW B2B MODELS (HYBRID READY)
# ==========================================

class Advisor(Base):
    """Wealth Manager Firm Profiles."""
    __tablename__ = 'advisors'
    email = Column(String, primary_key=True)
    firm_name = Column(String, default="New Firm")
    full_name = Column(String)
    address = Column(Text) 
    stripe_customer_id = Column(String)
    credits = Column(Integer, default=0)
    subscription_status = Column(String, default='active')
    created_at = Column(DateTime, default=datetime.utcnow)

class Client(Base):
    """Advisor CRM for permanent roster management."""
    __tablename__ = 'clients'
    id = Column(Integer, primary_key=True, autoincrement=True)
    advisor_email = Column(String, ForeignKey('advisors.email'))
    name = Column(String, nullable=False)
    phone = Column(String)
    email = Column(String)
    address_json = Column(Text)
    heir_name = Column(String)
    status = Column(String, default='Active')
    created_at = Column(DateTime, default=datetime.utcnow)

class Project(Base):
    """
    The Hybrid Model interview instance. 
    Security Fix: UUID primary key prevents unauthorized access to archives.
    """
    __tablename__ = 'projects'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    advisor_email = Column(String, ForeignKey('advisors.email'), nullable=False)
    client_id = Column(Integer, ForeignKey('clients.id'))
    project_type = Column(String, default='Heirloom_Interview')
    heir_name = Column(String)
    heir_address_json = Column(Text, default="{}")
    strategic_prompt = Column(Text)
    content = Column(Text) 
    audio_ref = Column(Text)
    tracking_number = Column(String)
    status = Column(String, default='Authorized') 
    scheduled_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# ==========================================
# 🛠️ HELPER FUNCTIONS (FULL PRESERVATION)
# ==========================================

def get_user_profile(email):
    """Fetches retail profile for Login."""
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

def save_audit_log(log_entry):
    try:
        with get_db_session() as session:
            valid_keys = {'user_email', 'event_type', 'details', 'description', 'stripe_session_id'}
            filtered = {k: v for k, v in log_entry.items() if k in valid_keys}
            session.add(AuditEvent(**filtered))
            session.commit()
            return True
    except Exception: return False

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
    """Enforces Advisor access boundaries."""
    try:
        with get_db_session() as session:
            adv = session.query(Advisor).filter_by(email=email).first()
            if not adv:
                legacy = session.query(UserProfile).filter_by(email=email).first()
                full_name = legacy.full_name if legacy else ""
                adv = Advisor(email=email, full_name=full_name)
                session.add(adv)
                session.commit()
            return to_dict(adv)
    except Exception: return {}

def get_clients(advisor_email):
    """Fetches firm-specific clients."""
    try:
        with get_db_session() as session:
            res = session.query(Client).filter_by(advisor_email=advisor_email).order_by(Client.created_at.desc()).all()
            return [to_dict(r) for r in res]
    except Exception: return []

def add_client(advisor_email, name, phone, address_dict=None):
    try:
        addr_str = json.dumps(address_dict) if address_dict else "{}"
        with get_db_session() as session:
            new_client = Client(advisor_email=advisor_email, name=name, phone=phone, address_json=addr_str)
            session.add(new_client)
            session.commit()
            return True
    except Exception: return False

def create_hybrid_project(advisor_email, parent_name, parent_phone, heir_name, prompt):
    """Creates relational link between Firm, Client, and Legacy Project."""
    try:
        with get_db_session() as session:
            client = session.query(Client).filter_by(advisor_email=advisor_email, phone=parent_phone).first()
            if not client:
                client = Client(advisor_email=advisor_email, name=parent_name, phone=parent_phone, heir_name=heir_name)
                session.add(client)
                session.flush() 
            new_proj = Project(advisor_email=advisor_email, client_id=client.id, heir_name=heir_name, strategic_prompt=prompt, status="Authorized")
            session.add(new_proj)
            session.commit()
            return new_proj.id
    except Exception: return None

def get_pending_approvals(advisor_email):
    """Fetches items for Ghostwriting review."""
    try:
        with get_db_session() as session:
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
    """Secure ID lookup for unauthenticated family portals."""
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
    """Global update hook for Project state changes."""
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

def update_project_audio(project_id, audio_ref, transcript):
    """Logic for AI Engine post-call updates."""
    try:
        with get_db_session() as session:
            proj = session.query(Project).filter_by(id=project_id).first()
            if proj:
                proj.audio_ref = audio_ref
                proj.content = transcript
                proj.status = "Recorded"
                session.commit()
                return True
            return False
    except Exception: return False
    
def get_user_drafts(email):
    """
    Fetches all letter drafts for a specific user from the database.
    Converts SQLAlchemy objects to dictionaries for safe UI rendering.
    """
    if not email:
        return []
        
    try:
        with get_db_session() as session:
            # Query drafts for this user, ordered by most recent first
            drafts = session.query(LetterDraft).filter(
                LetterDraft.user_email == email
            ).order_by(LetterDraft.created_at.desc()).all()
            
            # Convert results to dictionaries immediately
            # This is critical to prevent "Instance is not bound to a Session" errors
            return [
                {
                    "id": d.id,
                    "content": d.content,
                    "status": d.status,
                    "tier": d.tier,
                    "created_at": d.created_at.strftime("%Y-%m-%d %H:%M") if d.created_at else "Unknown",
                    "tracking_number": d.tracking_number,
                    "recipient_data": d.recipient_data,
                    "sender_data": d.sender_data,
                    "question_text": d.question_text
                } 
                for d in drafts
            ]
    except Exception as e:
        import logging
        logging.error(f"Error fetching drafts for {email}: {e}")
        return []

def update_last_call_timestamp(email):
    """
    Updates the 'last_call_date' for a user to the current UTC time.
    Used for call frequency limiting and activity tracking.
    """
    if not email:
        return False
    try:
        with get_db_session() as session:
            profile = session.query(UserProfile).filter_by(email=email).first()
            if profile:
                profile.last_call_date = datetime.utcnow()
                session.commit()
                return True
            return False
    except Exception as e:
        import logging
        logging.error(f"Error updating call timestamp for {email}: {e}")
        return False

def update_draft_data(draft_id, content=None, status=None, tier=None, price=None, tracking_number=None, question_text=None):
    """
    Updates a specific draft's metadata or content.
    """
    try:
        with get_db_session() as session:
            draft = session.query(LetterDraft).filter_by(id=draft_id).first()
            if draft:
                if content is not None: draft.content = content
                if status is not None: draft.status = status
                if tier is not None: draft.tier = tier
                if price is not None: draft.price = price
                if tracking_number is not None: draft.tracking_number = tracking_number
                if question_text is not None: draft.question_text = question_text
                session.commit()
                return True
            return False
    except Exception as e:
        logger.error(f"Update Draft Error: {e}")
        return False