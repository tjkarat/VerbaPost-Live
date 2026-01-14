import os
import logging
import urllib.parse
import json
import uuid
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, Float, DateTime, ForeignKey, text
from sqlalchemy.orm import sessionmaker, declarative_base
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
# 🏛️ MODELS
# ==========================================

class UserProfile(Base):
    """
    Standard User Table (Matches your provided schema).
    """
    __tablename__ = 'user_profiles'
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False)
    full_name = Column(String)
    parent_name = Column(String)
    parent_phone = Column(String)
    role = Column(String)
    
    # Address Fields
    address_line1 = Column(String)
    address_city = Column(String)
    address_state = Column(String)
    address_zip = Column(String)
    country = Column(String)
    timezone = Column(String)
    
    credits = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

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
    name = Column(String, nullable=False) # Parent Name
    phone = Column(String)
    email = Column(String) # Heir Email
    address_json = Column(Text)
    status = Column(String, default='Active')
    heir_name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class Project(Base):
    """
    The main work unit. Uses Integer ID to match DB Schema.
    """
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True, autoincrement=True) 
    
    advisor_email = Column(String, nullable=False)
    client_id = Column(Integer, ForeignKey('clients.id'))
    
    project_type = Column(String, default='Retainer_Letter')
    status = Column(String, default='Draft')
    content = Column(Text)
    audio_ref = Column(Text)
    tracking_number = Column(String)
    
    heir_name = Column(String)
    heir_address_json = Column(Text)
    
    # Features
    strategic_prompt = Column(Text)
    call_sid = Column(String)
    scheduled_time = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

class LetterDraft(Base):
    """Legacy Table for Store / One-off Letters"""
    __tablename__ = 'letter_drafts'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_email = Column(String)
    content = Column(Text)
    status = Column(String)
    call_sid = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class AuditEvent(Base):
    __tablename__ = 'audit_events'
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_email = Column(String)
    event_type = Column(String)
    details = Column(Text)
    description = Column(Text)
    stripe_session_id = Column(String)

class PaymentFulfillment(Base):
    __tablename__ = 'payment_fulfillments'
    stripe_session_id = Column(String, primary_key=True)
    product_name = Column(String)
    user_email = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

# ==========================================
# 🛠️ HELPER FUNCTIONS
# ==========================================

def get_user_profile(email):
    """
    Fetches User Profile.
    If the user is an Heir (Client), we dynamically enrich the profile with Advisor info.
    """
    try:
        with get_db_session() as session:
            # 1. Try to find user in user_profiles
            profile_obj = session.query(UserProfile).filter_by(email=email).first()
            if profile_obj:
                p = to_dict(profile_obj)
                # Ensure status is set
                if not p.get('status'):
                    p['status'] = "Active" if (p.get('credits', 0) > 0) else "Pending"
                return p

            # 2. If not in user_profiles, check if they are a Client (Heir)
            client = session.query(Client).filter_by(email=email).first()
            if client:
                # Build a virtual profile from the Client record
                adv = session.query(Advisor).filter_by(email=client.advisor_email).first()
                firm = adv.firm_name if adv else "VerbaPost"
                
                return {
                    "email": email,
                    "role": "heir",
                    "status": client.status,
                    "parent_name": client.name,
                    "parent_phone": client.phone,
                    "full_name": client.heir_name,
                    "advisor_firm": firm,
                    "advisor_email": client.advisor_email,
                    "type": "B2B"
                }

            # 3. New User
            return {"email": email, "role": "user", "status": "New"}
            
    except Exception as e:
        logger.error(f"Get Profile Error: {e}")
        return {}

def get_advisor_profile(email):
    try:
        with get_db_session() as session:
            adv = session.query(Advisor).filter_by(email=email).first()
            if adv: return to_dict(adv)
            return None
    except Exception as e:
        logger.error(f"Get Advisor Error: {e}")
        return None

def get_advisor_clients(email):
    try:
        with get_db_session() as session:
            res = session.query(Client).filter_by(advisor_email=email).order_by(Client.created_at.desc()).all()
            return [to_dict(r) for r in res]
    except Exception: return []

def create_b2b_project(advisor_email, client_name, client_phone, heir_name, heir_email, prompt):
    """Consumes credit and creates client/project records."""
    try:
        with get_db_session() as session:
            # 1. Check Credits
            adv = session.query(Advisor).filter_by(email=advisor_email).first()
            if not adv:
                # Auto-create advisor (Safety net for admin testing)
                adv = Advisor(email=advisor_email, firm_name="VerbaPost Wealth", credits=10)
                session.add(adv)
                session.flush()

            if adv.credits < 1:
                return False, "Insufficient Credits"
            
            # 2. Create Client
            new_client = Client(
                advisor_email=advisor_email,
                name=client_name,
                phone=client_phone,
                email=heir_email,
                heir_name=heir_name,
                status='Active'
            )
            session.add(new_client)
            session.flush() # Get ID
            
            # 3. Create Project
            # Note: We do NOT pass 'id' here. DB handles it (Serial).
            new_proj = Project(
                advisor_email=advisor_email,
                client_id=new_client.id,
                heir_name=heir_name,
                strategic_prompt=prompt,
                status='Authorized',
                created_at=datetime.utcnow()
            )
            session.add(new_proj)
            
            # 4. Deduct Credit
            adv.credits -= 1
            
        return True, "Project Created"
    except Exception as e:
        logger.error(f"Create B2B Project Error: {e}")
        return False, str(e)

def get_heir_projects(heir_email):
    try:
        with get_db_session() as session:
            client = session.query(Client).filter_by(email=heir_email).first()
            if not client: return []
            
            projects = session.query(Project).filter_by(client_id=client.id).order_by(Project.created_at.desc()).all()
            results = []
            for p in projects:
                d = to_dict(p)
                adv = session.query(Advisor).filter_by(email=p.advisor_email).first()
                d['firm_name'] = adv.firm_name if adv else "VerbaPost"
                results.append(d)
            return results
    except Exception: return []

def update_heirloom_settings(email, parent_name, parent_phone):
    try:
        with get_db_session() as session:
            # Check Client Table
            client = session.query(Client).filter_by(email=email).first()
            if client:
                client.name = parent_name
                client.phone = parent_phone
                session.commit()
                return True
            # Check User Table
            u = session.query(UserProfile).filter_by(email=email).first()
            if u:
                u.parent_name = parent_name
                u.parent_phone = parent_phone
                session.commit()
                return True
        return False
    except Exception: return False

def create_draft(user_email, content, status="Recording", call_sid=None, tier="Heirloom"):
    try:
        with get_db_session() as session:
            # Try to link to B2B Client first
            client = session.query(Client).filter_by(email=user_email).first()
            if client:
                new_proj = Project(
                    advisor_email=client.advisor_email,
                    client_id=client.id,
                    heir_name=client.heir_name,
                    strategic_prompt="Ad-hoc Interview",
                    status=status,
                    call_sid=call_sid,
                    created_at=datetime.utcnow()
                )
                session.add(new_proj)
                session.commit()
                return True
            
            # Fallback to Legacy Draft
            draft = LetterDraft(user_email=user_email, content=content, status=status, call_sid=call_sid)
            session.add(draft)
            session.commit()
            return True
    except Exception as e:
        logger.error(f"Create Draft Error: {e}")
        return False

def is_fulfillment_recorded(session_id):
    try:
        with get_db_session() as session:
            exists = session.query(PaymentFulfillment).filter_by(stripe_session_id=session_id).first()
            return exists is not None
    except Exception: return False

def record_stripe_fulfillment(session_id, product_name, user_email):
    try:
        with get_db_session() as session:
            f = PaymentFulfillment(stripe_session_id=session_id, product_name=product_name, user_email=user_email)
            session.add(f)
            session.commit()
            return True
    except Exception: return False

def add_advisor_credit(email, amount=1):
    try:
        with get_db_session() as session:
            adv = session.query(Advisor).filter_by(email=email).first()
            if adv:
                adv.credits += amount
                session.commit()
                return True
            return False
    except Exception: return False

def update_project_content(pid, new_text):
    try:
        with get_db_session() as session:
            # Check projects table
            p = session.query(Project).filter_by(id=pid).first()
            if p:
                p.content = new_text
                if p.status == 'Authorized': p.status = 'Recording'
                session.commit()
                return True
            # Check legacy table
            try:
                l = session.query(LetterDraft).filter_by(id=int(pid)).first()
                if l:
                    l.content = new_text
                    session.commit()
                    return True
            except: pass
        return False
    except Exception: return False

def submit_project(pid):
    try:
        with get_db_session() as session:
            p = session.query(Project).filter_by(id=pid).first()
            if p:
                p.status = 'Pending Approval'
                session.commit()
                return True
        return False
    except Exception: return False

def get_pending_approvals(advisor_email):
    """
    Fetches items that need Advisor Review.
    """
    try:
        with get_db_session() as session:
            projs = session.query(Project).filter_by(advisor_email=advisor_email, status="Pending Approval").all()
            results = []
            for p in projs:
                client = session.query(Client).filter_by(id=p.client_id).first()
                d = to_dict(p)
                d['parent_name'] = client.name if client else "Unknown"
                d['heir_name'] = client.heir_name if client else "Unknown"
                results.append(d)
            return results
    except Exception: return []

def update_project_details(project_id, content=None, status=None):
    """
    Admin override / Legacy update
    """
    try:
        with get_db_session() as session:
            proj = session.query(Project).filter_by(id=project_id).first()
            if proj:
                if status: proj.status = status
                if content: proj.content = content
                session.commit()
                return True
            return False
    except Exception: return False

def log_event(user_email, event_type, metadata=None):
    try:
        details_str = json.dumps(metadata) if metadata else ""
        with get_db_session() as session:
            evt = AuditEvent(user_email=user_email, event_type=event_type, details=details_str)
            session.add(evt)
            session.commit()
    except Exception: pass