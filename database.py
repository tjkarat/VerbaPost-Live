import os
import logging
import urllib.parse
import json
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, Float, DateTime, ForeignKey, text
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import contextmanager
from datetime import datetime
import streamlit as st

# --- IMPORT SECRETS ---
try: import secrets_manager
except ImportError: secrets_manager = None

# --- 1. SUPABASE CLIENT SETUP (REQUIRED FOR NEW B2B FUNCTIONS) ---
try:
    from supabase import create_client, Client
    
    sb_url = os.environ.get("SUPABASE_URL")
    sb_key = os.environ.get("SUPABASE_KEY")
    
    if not sb_url and secrets_manager:
        sb_url = secrets_manager.get_secret("supabase.url")
        sb_key = secrets_manager.get_secret("supabase.key")
        
    if not sb_url and hasattr(st, "secrets") and "supabase" in st.secrets:
        sb_url = st.secrets["supabase"]["url"]
        sb_key = st.secrets["supabase"]["key"]

    if sb_url and sb_key:
        supabase: Client = create_client(sb_url, sb_key)
    else:
        supabase = None
except ImportError:
    supabase = None

logger = logging.getLogger(__name__)
Base = declarative_base()

# --- 2. SQLALCHEMY SETUP (REQUIRED FOR LEGACY FUNCTIONS) ---
_engine = None
_SessionLocal = None

def get_db_url():
    if not secrets_manager: return os.environ.get("DATABASE_URL")
    try:
        url = secrets_manager.get_secret("DATABASE_URL")
        if url: return url
        sb_url = secrets_manager.get_secret("supabase.url")
        sb_key = secrets_manager.get_secret("supabase.key")
        sb_pass = secrets_manager.get_secret("supabase.db_password")
        if sb_url and sb_pass:
            encoded_pass = urllib.parse.quote_plus(sb_pass)
            clean_host = sb_url.replace("https://", "").replace("/", "")
            return f"postgresql://postgres:{encoded_pass}@{clean_host}:5432/postgres"
        return None
    except Exception: return None

def init_db():
    global _engine, _SessionLocal
    if _engine is not None: return _engine, _SessionLocal
    url = get_db_url()
    if not url: return None, None
    try:
        _engine = create_engine(url, pool_pre_ping=True)
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
        Base.metadata.create_all(_engine)
        return _engine, _SessionLocal
    except Exception: return None, None

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
# 🏛️ MODELS (ALL ORIGINAL MODELS RESTORED)
# ==========================================

class UserProfile(Base):
    __tablename__ = 'user_profiles'
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False)
    full_name = Column(String)
    parent_name = Column(String)
    parent_phone = Column(String)
    role = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    address_line1 = Column(String)
    address_city = Column(String)
    address_state = Column(String)
    address_zip = Column(String)
    country = Column(String)
    timezone = Column(String)
    advisor_firm = Column(String)
    credits = Column(Integer, default=0)

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
    heir_name = Column(String)
    parent_email = Column(String)
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
    heir_name = Column(String)
    heir_address_json = Column(Text)
    strategic_prompt = Column(Text)
    call_sid = Column(String)
    scheduled_time = Column(DateTime, nullable=True)
    audio_released = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class LetterDraft(Base):
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
# 🛠️ HELPER FUNCTIONS (LEGACY RESTORED)
# ==========================================

def fix_heir_account(email):
    email = email.strip().lower()
    try:
        with get_db_session() as session:
            clients = session.query(Client).filter_by(email=email).order_by(Client.created_at.desc()).all()
            if not clients: return False
            winner = clients[0]
            if winner.status != 'Active':
                winner.status = 'Active'
                session.add(winner)
            if len(clients) > 1:
                for loser in clients[1:]:
                    session.delete(loser)
            u = session.query(UserProfile).filter_by(email=email).first()
            if u: u.role = 'heir'
            session.commit()
            return True
    except Exception: return False

def create_user(email, full_name, role='user'):
    email = email.strip().lower()
    try:
        with get_db_session() as session:
            existing = session.query(UserProfile).filter_by(email=email).first()
            if existing: return True 
            u = UserProfile(email=email, full_name=full_name, role=role)
            session.add(u)
            session.commit()
            return True
    except Exception: return False

def get_user_profile(email):
    email = email.strip().lower()
    try:
        with get_db_session() as session:
            profile_obj = session.query(UserProfile).filter_by(email=email).first()
            p = to_dict(profile_obj) if profile_obj else {"email": email}
            client = session.query(Client).filter_by(email=email).order_by(Client.created_at.desc()).first()
            if client:
                adv = session.query(Advisor).filter_by(email=client.advisor_email).first()
                firm = adv.firm_name if adv else "VerbaPost"
                p["role"] = "heir"
                p["status"] = "Active" 
                p["advisor_firm"] = firm
                p["advisor_email"] = client.advisor_email
                if client.name: p["parent_name"] = client.name
                if client.phone: p["parent_phone"] = client.phone
            if "role" not in p: p["role"] = "user"
            return p
    except Exception: return {}

def get_advisor_profile(email):
    email = email.strip().lower()
    try:
        with get_db_session() as session:
            adv = session.query(Advisor).filter_by(email=email).first()
            if adv: return to_dict(adv)
            return None
    except Exception: return None

def get_advisor_clients(email):
    email = email.strip().lower()
    try:
        with get_db_session() as session:
            res = session.query(Client).filter_by(advisor_email=email).order_by(Client.created_at.desc()).all()
            return [to_dict(r) for r in res]
    except Exception: return []

def create_b2b_project(advisor_email, client_name, client_phone, heir_name, heir_email, prompt, parent_email=None):
    advisor_email = advisor_email.strip().lower()
    heir_email = heir_email.strip().lower()
    if parent_email: parent_email = parent_email.strip().lower()
    try:
        with get_db_session() as session:
            adv = session.query(Advisor).filter_by(email=advisor_email).first()
            if not adv:
                adv = Advisor(email=advisor_email, firm_name="VerbaPost Wealth", credits=0)
                session.add(adv)
                session.flush()
            if adv.credits < 1: return False, "Insufficient Credits"
            
            new_client = Client(
                advisor_email=advisor_email,
                name=client_name,
                phone=client_phone,
                email=heir_email, 
                parent_email=parent_email,
                heir_name=heir_name,
                status='Active'
            )
            session.add(new_client)
            session.flush() 
            
            new_proj = Project(
                advisor_email=advisor_email,
                client_id=new_client.id,
                heir_name=heir_name,
                strategic_prompt=prompt,
                status='Authorized'
            )
            session.add(new_proj)
            adv.credits -= 1
        return True, "Project Created"
    except Exception as e: return False, str(e)

def get_heir_projects(heir_email):
    heir_email = heir_email.strip().lower()
    try:
        with get_db_session() as session:
            client = session.query(Client).filter_by(email=heir_email).order_by(Client.created_at.desc()).first()
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

def update_heirloom_settings(email, parent_name, parent_phone, addr1=None, city=None, state=None, zip_code=None):
    email = email.strip().lower()
    try:
        with get_db_session() as session:
            client = session.query(Client).filter_by(email=email).order_by(Client.created_at.desc()).first()
            if client:
                client.name = parent_name
                client.phone = parent_phone
            u = session.query(UserProfile).filter_by(email=email).first()
            if u:
                u.parent_name = parent_name
                u.parent_phone = parent_phone
                if addr1: u.address_line1 = addr1
                if city: u.address_city = city
                if state: u.address_state = state
                if zip_code: u.address_zip = zip_code
            session.commit()
            return True
    except Exception: return False

def create_draft(user_email, content, status="Recording", call_sid=None):
    user_email = user_email.strip().lower()
    try:
        with get_db_session() as session:
            client = session.query(Client).filter_by(email=user_email).order_by(Client.created_at.desc()).first()
            if client:
                new_proj = Project(
                    advisor_email=client.advisor_email,
                    client_id=client.id,
                    heir_name=client.heir_name,
                    strategic_prompt="Ad-hoc Interview",
                    status=status,
                    call_sid=call_sid
                )
                session.add(new_proj)
                session.commit()
                return True
            draft = LetterDraft(user_email=user_email, content=content, status=status, call_sid=call_sid)
            session.add(draft)
            session.commit()
            return True
    except Exception: return False

def is_fulfillment_recorded(session_id):
    try:
        with get_db_session() as session:
            return session.query(PaymentFulfillment).filter_by(stripe_session_id=session_id).first() is not None
    except Exception: return False

def record_stripe_fulfillment(session_id, product_name, user_email):
    try:
        with get_db_session() as session:
            f = PaymentFulfillment(stripe_session_id=session_id, product_name=product_name, user_email=user_email)
            session.add(f)
            session.commit()
            return True
    except Exception: return False

def update_project_content(pid, new_text):
    try:
        with get_db_session() as session:
            p = session.query(Project).filter_by(id=pid).first()
            if p:
                p.content = new_text
                session.commit()
                return True
            try:
                l = session.query(LetterDraft).filter_by(id=int(pid)).first()
                if l:
                    l.content = new_text
                    session.commit()
                    return True
            except: pass
        return False
    except Exception: return False

def finalize_heir_project(pid, content):
    try:
        with get_db_session() as session:
            p = session.query(Project).filter_by(id=pid).first()
            if p:
                p.content = content
                p.status = 'Approved' 
                session.commit()
                return True
        return False
    except Exception: return False

def toggle_media_release(pid, release=True):
    try:
        with get_db_session() as session:
            p = session.query(Project).filter_by(id=pid).first()
            if p:
                p.audio_released = release
                session.commit()
                return True
        return False
    except Exception: return False

def get_advisor_projects_for_media(advisor_email):
    advisor_email = advisor_email.strip().lower()
    try:
        with get_db_session() as session:
            projects = session.query(Project).filter_by(advisor_email=advisor_email).all()
            results = []
            for p in projects:
                d = to_dict(p)
                client = session.query(Client).filter_by(id=p.client_id).first()
                d['heir_name'] = client.heir_name if client else "Unknown"
                d['heir_email'] = client.email if client else "Unknown"
                results.append(d)
            return results
    except Exception: return []

def update_project_details(project_id, content=None, status=None):
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

def get_project_by_id(pid):
    try:
        with get_db_session() as session:
            proj = session.query(Project).filter_by(id=pid).first()
            if proj:
                d = to_dict(proj)
                client = session.query(Client).filter_by(id=proj.client_id).first()
                if client:
                    d['parent_name'] = client.name
                    d['heir_name'] = client.heir_name
                
                # Fetch Firm Name from Advisor table
                adv = session.query(Advisor).filter_by(email=proj.advisor_email).first()
                if adv:
                    d['firm_name'] = adv.firm_name
                else:
                    d['firm_name'] = "VerbaPost Wealth"
                    
                return d
            return None
    except Exception: return None

def log_event(user_email, event_type, metadata=None):
    try:
        details_str = json.dumps(metadata) if metadata else ""
        with get_db_session() as session:
            evt = AuditEvent(user_email=user_email, event_type=event_type, details=details_str)
            session.add(evt)
            session.commit()
    except Exception: pass

# ==========================================
# 🆕 NEW B2B FUNCTIONS (FIXED)
# ==========================================

def fetch_advisor_clients(advisor_email):
    """Fetches clients for the Advisor Portal."""
    if not supabase: return []
    try:
        response = supabase.table("user_profiles").select("*").eq("created_by", advisor_email).execute()
        return response.data
    except Exception as e:
        logger.error(f"Error fetching clients: {e}")
        return []

def get_user_drafts(user_email):
    """
    Fetches stories. 
    FIX: Queries 'projects' table via 'clients' lookup (since projects table lacks user_email).
    """
    if not supabase: return []
    try:
        # 1. Get Client ID from 'clients' table
        client_res = supabase.table("clients").select("id").eq("email", user_email).execute()
        
        # If no client record, they have no projects
        if not client_res.data:
            return []
            
        client_id = client_res.data[0]['id']
        
        # 2. Get Projects for this Client
        # Note: Using 'projects' table now, not 'posts'
        response = supabase.table("projects").select("*").eq("client_id", client_id).order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        logger.error(f"Error fetching drafts: {e}")
        return []

def create_sponsored_user(advisor_email, client_name, client_email, client_phone):
    """
    Creates a new client account.
    FIX: Inserts into BOTH 'user_profiles' AND 'clients' to maintain B2B relationships.
    """
    if not supabase: return False, "DB Offline"

    try:
        # 1. Check if user exists
        existing = supabase.table("user_profiles").select("id").eq("email", client_email).execute()
        if existing.data:
            return False, "User with this email already exists."

        # 2. Create User Profile (Login Access)
        new_profile = {
            "email": client_email,
            "full_name": client_name,
            "parent_phone": client_phone,
            "created_by": advisor_email, # Link to Advisor
            "role": "heirloom",
            "credits": 0,
            "advisor_firm": "Robbana and Associates" # Should fetch actual firm name in production
        }
        supabase.table("user_profiles").insert(new_profile).execute()
        
        # 3. Create Client Record (Project Linkage)
        # We need this so 'get_user_drafts' works!
        new_client = {
            "email": client_email,
            "name": client_name,
            "phone": client_phone,
            "advisor_email": advisor_email,
            "status": "Active"
        }
        supabase.table("clients").insert(new_client).execute()
        
        return True, "Client account created successfully."
            
    except Exception as e:
        logger.error(f"Error creating sponsored user: {e}")
        return False, str(e)

def update_advisor_firm_name(advisor_email, new_firm_name):
    if not supabase: return False
    try:
        supabase.table("user_profiles").update({"advisor_firm": new_firm_name}).eq("email", advisor_email).execute()
        return True
    except Exception as e:
        logger.error(f"Update Firm Error: {e}")
        return False

def update_user_credits(user_email, new_amount):
    if not supabase: return False
    try:
        supabase.table("user_profiles").update({"credits": new_amount}).eq("email", user_email).execute()
        return True
    except Exception: return False

def mark_draft_sent(draft_id, letter_id):
    if not supabase: return False
    try:
        # FIX: Targeting 'projects' table
        supabase.table("projects").update({"status": "sent", "tracking_number": letter_id}).eq("id", draft_id).execute()
        return True
    except: return False

def update_draft(draft_id, new_text):
    if not supabase: return False
    try:
        # FIX: Targeting 'projects' table
        supabase.table("projects").update({"content": new_text}).eq("id", draft_id).execute()
        return True
    except: return False

# --- 🟡 FIX: REWRITTEN CREDIT FUNCTION ---
def add_advisor_credit(email, amount=1):
    """
    Increments credits in the user_profiles table (B2B Logic).
    """
    # 1. Try Supabase Client First (Preferred)
    if supabase:
        try:
            # Fetch current
            res = supabase.table("user_profiles").select("credits").eq("email", email).execute()
            if res.data:
                current = res.data[0].get('credits', 0) or 0
                new_total = current + amount
                supabase.table("user_profiles").update({"credits": new_total}).eq("email", email).execute()
                return True
        except Exception as e:
            logger.error(f"Credit Update Failed: {e}")
            # Do NOT return False yet, try Fallback

    # 2. Fallback to SQLAlchemy (Legacy) - BUT UPDATE USER_PROFILES
    try:
        with get_db_session() as session:
            # TARGET USER_PROFILE (NOT ADVISOR TABLE)
            u = session.query(UserProfile).filter_by(email=email).first()
            if u:
                u.credits = (u.credits or 0) + amount
                session.commit()
                return True
    except: return False
    return False