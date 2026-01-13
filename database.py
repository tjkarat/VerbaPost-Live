import os
import logging
import urllib.parse
import json
import uuid
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, Float, DateTime, ForeignKey, BigInteger, text, Identity
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
# 🏛️ MODELS (Unified B2B Schema)
# ==========================================

class UserProfile(Base):
    """Identity management."""
    __tablename__ = 'user_profiles'
    
    # FIX: Added ID to handle legacy schema requirements
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    email = Column(String, unique=True, nullable=False)
    full_name = Column(String)
    parent_name = Column(String)
    parent_phone = Column(String)
    role = Column(String, default="user") # user, advisor, admin
    created_at = Column(DateTime, default=datetime.utcnow)
    advisor_email = Column(String, nullable=True) 
    
    # FIX: Added advisor_firm to prevent AttributeError
    advisor_firm = Column(String, nullable=True)

    # Legacy fields preserved to prevent migration errors
    address_line1 = Column(String)
    address_city = Column(String)
    address_state = Column(String)
    address_zip = Column(String)
    country = Column(String, default="US")
    timezone = Column(String, default="US/Central")

class Advisor(Base):
    """Wealth Manager Firm Profiles."""
    __tablename__ = 'advisors'
    email = Column(String, primary_key=True)
    firm_name = Column(String, default="New Firm")
    full_name = Column(String)
    credits = Column(Integer, default=0) # $99 Activations purchased
    created_at = Column(DateTime, default=datetime.utcnow)

class Client(Base):
    """Advisor CRM Roster."""
    __tablename__ = 'clients'
    id = Column(Integer, primary_key=True, autoincrement=True)
    advisor_email = Column(String, ForeignKey('advisors.email'))
    name = Column(String) # Parent Name
    phone = Column(String) # Parent Phone
    email = Column(String) # Heir Email (Login ID)
    heir_name = Column(String)
    status = Column(String, default='Active')
    created_at = Column(DateTime, default=datetime.utcnow)
    address_json = Column(Text, default="{}")

class Project(Base):
    """The Core Unit of Work."""
    __tablename__ = 'projects'
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    advisor_email = Column(String, ForeignKey('advisors.email'), nullable=False)
    client_id = Column(Integer, ForeignKey('clients.id'))
    
    # Metadata
    heir_name = Column(String)
    heir_address_json = Column(Text)
    strategic_prompt = Column(Text)
    
    # Content
    content = Column(Text) 
    audio_ref = Column(Text)
    
    # State
    status = Column(String, default='Authorized') 
    scheduled_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class AuditEvent(Base):
    """System Logs."""
    __tablename__ = 'audit_events'
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_email = Column(String)
    event_type = Column(String)
    details = Column(Text)
    description = Column(Text) # Legacy support
    stripe_session_id = Column(String) # Legacy support

class PaymentFulfillment(Base):
    """Idempotency for Stripe Webhooks."""
    __tablename__ = 'payment_fulfillments'
    stripe_session_id = Column(String, primary_key=True)
    product_name = Column(String)
    user_email = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

# ==========================================
# 🛠️ HELPER FUNCTIONS (B2B FOCUSED)
# ==========================================

def get_user_profile(email):
    """Fetches profile, creating one if it doesn't exist."""
    try:
        with get_db_session() as session:
            profile = session.query(UserProfile).filter_by(email=email).first()
            if not profile:
                profile = UserProfile(email=email)
                session.add(profile)
                session.commit()
            return to_dict(profile)
    except Exception as e:
        logger.error(f"Get Profile Error: {e}")
        return {}

def update_heirloom_settings(email, parent_name, parent_phone):
    """Updates the user's interview target."""
    try:
        with get_db_session() as session:
            u = session.query(UserProfile).filter_by(email=email).first()
            if u:
                u.parent_name = parent_name
                u.parent_phone = parent_phone
                session.commit()
                return True
            return False
    except Exception: return False

def create_user(email, full_name):
    """Creates a basic user profile (used by signup)."""
    try:
        with get_db_session() as db:
            # We don't pass ID; we rely on DB autoincrement
            user = UserProfile(email=email, full_name=full_name)
            db.add(user)
            db.commit()
            return True
    except Exception as e:
        logger.error(f"Create User Error: {e}")
        return False

# --- ADVISOR / B2B LOGIC ---

def get_or_create_advisor(email):
    """Enforces Advisor access boundaries."""
    try:
        with get_db_session() as session:
            adv = session.query(Advisor).filter_by(email=email).first()
            if not adv:
                # Fallback: Try to get data from UserProfile
                legacy = session.query(UserProfile).filter_by(email=email).first()
                full_name = legacy.full_name if legacy else ""
                
                # FIX: Handle potential NoneType for legacy or advisor_firm
                firm_name = getattr(legacy, 'advisor_firm', "Independent Firm")
                if not firm_name: firm_name = "Independent Firm"

                adv = Advisor(email=email, full_name=full_name, firm_name=firm_name)
                session.add(adv)
                session.commit()
            return to_dict(adv)
    except Exception as e: 
        logger.error(f"Advisor Create Error: {e}")
        return {}

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
            # Check if client exists, else create
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
    except Exception as e: 
        logger.error(f"Create Project Error: {e}")
        return None

def get_pending_approvals(advisor_email):
    """Fetches items for Ghostwriting review."""
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
    """Global update hook for Project state changes."""
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

# --- CREDIT & PAYMENT LOGIC ---

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

def deduct_advisor_credit(email, amount=1):
    try:
        with get_db_session() as session:
            adv = session.query(Advisor).filter_by(email=email).first()
            if adv and adv.credits >= amount:
                adv.credits -= amount
                session.commit()
                return True
            return False
    except Exception: return False

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

# --- HEIR / PROJECT LOGIC ---

def get_heir_projects(heir_email):
    """
    Fetches all projects linked to this Heir's email via the Client table.
    """
    try:
        with get_db_session() as session:
            # 1. Find Client ID matching this email
            client = session.query(Client).filter_by(email=heir_email).first()
            if not client:
                return []
            
            # 2. Find Projects for this Client
            projects = session.query(Project).filter_by(client_id=client.id).order_by(Project.created_at.desc()).all()
            
            # 3. Enrich with Advisor Info (Firm Name)
            results = []
            for p in projects:
                d = to_dict(p)
                adv = session.query(Advisor).filter_by(email=p.advisor_email).first()
                d['firm_name'] = adv.firm_name if adv else "VerbaPost"
                results.append(d)
            return results
    except Exception as e:
        logger.error(f"Get Projects Error: {e}")
        return []

def update_project_content(project_id, content):
    """Heir editing the transcript."""
    try:
        with get_db_session() as session:
            p = session.query(Project).filter_by(id=project_id).first()
            if p and p.status in ['Recording', 'Authorized']:
                p.content = content
                if p.status == 'Authorized': p.status = 'Recording'
                session.commit()
                return True
            return False
    except Exception: return False

def submit_project(project_id):
    """
    Heir submits story to Advisor. 
    Moves status: Recording -> Pending Approval
    """
    try:
        with get_db_session() as session:
            p = session.query(Project).filter_by(id=project_id).first()
            if p:
                p.status = "Pending Approval"
                session.commit()
                return True
            return False
    except Exception: return False

def log_event(user_email, event_type, details=""):
    try:
        with get_db_session() as session:
            evt = AuditEvent(user_email=user_email, event_type=event_type, details=str(details))
            session.add(evt)
            session.commit()
    except Exception: pass