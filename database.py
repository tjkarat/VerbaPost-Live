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

# --- 1. SUPABASE CLIENT SETUP ---
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

# --- 2. SQLALCHEMY SETUP ---
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
# 🏛️ MODELS
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
    tracking_number = Column(String) # Ensure this exists in your DB or add it manually if missing

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
    email = email.strip().lower()
    try:
        with get_db_session() as session:
            profile_obj = session.query(UserProfile).filter_by(email=email).first()
            if not profile_obj:
                legacy_adv = session.query(Advisor).filter_by(email=email).first()
                if legacy_adv:
                    profile_obj = UserProfile(
                        email=email,
                        full_name=legacy_adv.full_name,
                        role="advisor",
                        advisor_firm=legacy_adv.firm_name,
                        credits=legacy_adv.credits,
                        created_at=legacy_adv.created_at or datetime.utcnow()
                    )
                    session.add(profile_obj)
                    session.commit()
                    session.refresh(profile_obj)
            
            p = to_dict(profile_obj) if profile_obj else {"email": email}
            if p.get("role") != "advisor":
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

def get_advisor_clients(email):
    email = email.strip().lower()
    try:
        with get_db_session() as session:
            res = session.query(Client).filter_by(advisor_email=email).order_by(Client.created_at.desc()).all()
            return [to_dict(r) for r in res]
    except Exception: return []

def create_draft(user_email, content, status="Recording", call_sid=None, prompt=None):
    user_email = user_email.strip().lower()
    # If no prompt provided, fallback to "Ad-hoc Interview"
    final_prompt = prompt if prompt else "Ad-hoc Interview" 
    
    try:
        with get_db_session() as session:
            client = session.query(Client).filter_by(email=user_email).order_by(Client.created_at.desc()).first()
            if client:
                new_proj = Project(
                    advisor_email=client.advisor_email,
                    client_id=client.id,
                    heir_name=client.heir_name,
                    strategic_prompt=final_prompt, # <--- SAVES THE ACTUAL QUESTION
                    status=status,
                    call_sid=call_sid,
                    content=content
                )
                session.add(new_proj)
                session.commit()
                return True
            
            # Fallback for non-client drafts
            draft = LetterDraft(user_email=user_email, content=content, status=status, call_sid=call_sid)
            session.add(draft)
            session.commit()
            return True
    except Exception as e:
        logger.error(f"Create Draft Error: {e}")
        return False
    
def update_draft_by_sid(call_sid, content, recording_url):
    try:
        with get_db_session() as session:
            p = session.query(Project).filter_by(call_sid=call_sid).first()
            if p:
                p.content = content
                p.tracking_number = recording_url 
                p.status = 'Draft'
                p.call_sid = None 
                session.commit()
                return True
            d = session.query(LetterDraft).filter_by(call_sid=call_sid).first()
            if d:
                d.content = content
                d.status = 'Draft'
                d.call_sid = None
                d.tracking_number = recording_url # Store URL here if using LetterDraft
                session.commit()
                return True
        return False
    except Exception as e:
        logger.error(f"Update SID Error: {e}")
        return False

# --- 🔴 RESTORED: ADVISOR MEDIA LOOKUP ---
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

# --- 🔴 RESTORED: MANUAL MAILING HELPER ---
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
                adv = session.query(Advisor).filter_by(email=proj.advisor_email).first()
                if adv: d['firm_name'] = adv.firm_name
                else: d['firm_name'] = "VerbaPost Wealth"
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
# 🆕 NEW B2B FUNCTIONS (USING SUPABASE CLIENT)
# ==========================================

def fetch_advisor_clients(advisor_email):
    if not supabase: return []
    try:
        response = supabase.table("user_profiles").select("*").eq("created_by", advisor_email).execute()
        return response.data
    except Exception as e:
        logger.error(f"Error fetching clients: {e}")
        return []

def get_user_drafts(user_email):
    if not supabase: return []
    try:
        client_res = supabase.table("clients").select("id").eq("email", user_email).execute()
        if not client_res.data: return []
        client_id = client_res.data[0]['id']
        # Fetch Project Table
        response = supabase.table("projects").select("*").eq("client_id", client_id).order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        logger.error(f"Error fetching drafts: {e}")
        return []

# --- 🚨 CRITICAL FIX: UPDATED LOGIC FOR EXISTING USERS 🚨 ---
def create_sponsored_user(advisor_email, client_name, client_email, client_phone):
    if not supabase: return False, "DB Offline"
    try:
        # 1. Check if the User Profile already exists
        existing_profile = supabase.table("user_profiles").select("id").eq("email", client_email).execute()
        
        # 2. If they are NEW, create the User Profile
        if not existing_profile.data:
            new_profile = {
                "email": client_email, 
                "full_name": client_name, 
                "parent_phone": client_phone,
                "created_by": advisor_email, 
                "role": "heirloom", 
                "credits": 0, # Changed to 0 so you don't give away free credits unless intended
                "advisor_firm": "Robbana and Associates" # Default firm fallback
            }
            supabase.table("user_profiles").insert(new_profile).execute()
            
        # 3. Check if they are ALREADY in this Advisor's roster (Prevent Duplicates)
        existing_client_link = supabase.table("clients").select("id").eq("email", client_email).eq("advisor_email", advisor_email).execute()
        
        if existing_client_link.data:
            return False, "Client already in your roster"

        # 4. Create the Client Roster Link (The Project)
        new_client = {
            "email": client_email, 
            "name": client_name, 
            "phone": client_phone,
            "advisor_email": advisor_email, 
            "status": "Active"
        }
        supabase.table("clients").insert(new_client).execute()
        
        return True, "Success"
    except Exception as e: return False, str(e)

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
        supabase.table("projects").update({"status": "sent", "tracking_number": letter_id}).eq("id", draft_id).execute()
        return True
    except: return False

def update_draft(draft_id, new_text):
    if not supabase: return False
    try:
        supabase.table("projects").update({"content": new_text}).eq("id", draft_id).execute()
        return True
    except: return False

def add_advisor_credit(email, amount=1):
    if supabase:
        try:
            res = supabase.table("user_profiles").select("credits").eq("email", email).execute()
            if res.data:
                current = res.data[0].get('credits', 0) or 0
                supabase.table("user_profiles").update({"credits": current + amount}).eq("email", email).execute()
                return True
        except Exception as e: logger.error(f"Credit Update Failed: {e}")

    try:
        with get_db_session() as session:
            u = session.query(UserProfile).filter_by(email=email).first()
            if u:
                u.credits = (u.credits or 0) + amount
                session.commit()
                return True
    except: return False
    return False

# ==========================================
# 🆕 PUBLIC PLAYER ACCESS (FIX FOR QR CODE)
# ==========================================

def get_public_draft(draft_id):
    """
    Fetches a draft by ID for the public player (QR Code).
    Securely returns only the necessary metadata and URL.
    Checks 'projects' table first, then 'letter_drafts'.
    """
    try:
        # Cast ID to int to prevent SQL injection attempts via URL
        try:
            safe_id = int(str(draft_id).strip())
        except ValueError:
            return None
            
        with get_db_session() as db:
            # 1. Check PROJECT table (B2B Priority)
            proj = db.query(Project).filter(Project.id == safe_id).first()
            if proj:
                return {
                    "id": proj.id,
                    "url": proj.tracking_number, # This holds the Audio URL
                    "title": f"Story #{proj.id}",
                    "date": proj.created_at.strftime("%B %d, %Y") if proj.created_at else "Unknown",
                    "storyteller": proj.heir_name or "Family Member"
                }

            # 2. Check LETTER_DRAFT table (Legacy/B2C)
            draft = db.query(LetterDraft).filter(LetterDraft.id == safe_id).first()
            if draft:
                return {
                    "id": draft.id,
                    "url": draft.tracking_number,
                    "title": f"Story #{draft.id}",
                    "date": draft.created_at.strftime("%B %d, %Y") if draft.created_at else "Unknown",
                    "storyteller": "Family Member"
                }
            return None
    except Exception as e:
        logger.error(f"Public Draft Fetch Error: {e}")
        return None