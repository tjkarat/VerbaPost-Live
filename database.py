import os
import logging
import urllib.parse
import json
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, Float, DateTime, ForeignKey, text
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import contextmanager
from datetime import datetime

# Optional Streamlit: the FastAPI backend runs without it. The stub makes
# `hasattr(st, "secrets")` / `"x" in st.secrets` behave safely (False/empty).
try:
    import streamlit as st
except ImportError:
    class _StreamlitStub:
        secrets = {}
        def __getattr__(self, _name):
            def _noop(*args, **kwargs):
                return None
            return _noop
    st = _StreamlitStub()

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
except Exception as _sb_err:
    # Broadened from ImportError: create_client can also raise on
    # key-format problems. A dead Supabase client must never make
    # `import database` itself crash — SQLAlchemy paths still work.
    logging.getLogger(__name__).error(f"Supabase client init failed: {_sb_err}")
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

class Recipient(Base):
    """Additional family members who receive a printed copy of each story.
    The heir's own address is implicit; up to 4 more may be added (5 letters
    total per story — included in the engagement, no extra fee)."""
    __tablename__ = 'recipients'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_email = Column(String, nullable=False)
    name = Column(String, nullable=False)
    street = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)
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
# 🆕 PROSPECT ACQUISITION PATH (advisor-branded free letter)
# ==========================================

class AdvisorPage(Base):
    """One advisor-branded landing page per advisor (/a/{slug}).
    The advisor's name and firm go on the site AND on the envelope, so the
    return address lives here rather than on user_profiles."""
    __tablename__ = 'advisor_pages'
    id = Column(Integer, primary_key=True, autoincrement=True)
    advisor_email = Column(String, unique=True, nullable=False)
    slug = Column(String, unique=True, nullable=False)
    display_name = Column(String, nullable=False)
    firm_name = Column(String)
    headline = Column(String)
    intro = Column(Text)
    prompt = Column(Text)                 # the interview question the biographer asks
    photo_data = Column(Text)             # base64 image (kept small; served via /a/{slug}/photo)
    photo_mime = Column(String)
    return_line1 = Column(String)
    return_city = Column(String)
    return_state = Column(String)
    return_zip = Column(String)
    disclosure = Column(Text)             # advisor's compliance footer (e.g. "Securities offered through…")
    invite_body = Column(Text)            # invitation letter body (mailed to the uploaded list)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProspectLetter(Base):
    """The SEND LOG. One row per prospect intake — this table is the
    advertising-records export. Rows are never deleted; status moves
    forward: consented -> dnc_blocked | calling -> recorded -> Approved -> Sent."""
    __tablename__ = 'prospect_letters'
    id = Column(Integer, primary_key=True, autoincrement=True)
    advisor_email = Column(String, nullable=False)
    page_id = Column(Integer, ForeignKey('advisor_pages.id'))
    # the operator (storyteller)
    prospect_name = Column(String, nullable=False)
    prospect_phone = Column(String, nullable=False)   # E.164
    # the person they name
    recipient_name = Column(String, nullable=False)
    recipient_line1 = Column(String, nullable=False)
    recipient_city = Column(String, nullable=False)
    recipient_state = Column(String, nullable=False)
    recipient_zip = Column(String, nullable=False)
    # express written consent (TCPA / E-SIGN record)
    consent_version = Column(String)
    consent_text = Column(Text)
    consent_at = Column(DateTime)
    consent_ip = Column(String)
    consent_user_agent = Column(String)
    # DNC scrub
    dnc_status = Column(String)          # clear | listed | internal_only | error
    dnc_provider = Column(String)
    dnc_checked_at = Column(DateTime)
    # telephony + content
    call_sid = Column(String)
    call_attempts = Column(Integer, default=0)
    last_call_at = Column(DateTime)
    audio_url = Column(Text)
    transcript_raw = Column(Text)
    letter_text = Column(Text)
    letter_version = Column(String)      # which letter template rendered it
    status = Column(String, default='consented')
    queued_at = Column(DateTime)
    sent_at = Column(DateTime)
    invitation_id = Column(Integer)      # set when the prospect arrived via a mailed invitation's personal link
    created_at = Column(DateTime, default=datetime.utcnow)


class ProspectCampaign(Base):
    """One uploaded mailing list = one campaign. Invitations are the billable
    unit: every invitation mailed consumes one ledger credit."""
    __tablename__ = 'prospect_campaigns'
    id = Column(Integer, primary_key=True, autoincrement=True)
    advisor_email = Column(String, nullable=False)
    page_id = Column(Integer, ForeignKey('advisor_pages.id'))
    name = Column(String)
    status = Column(String, default='draft')     # draft | sending | sent | partial
    total_rows = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime)


class CampaignInvitation(Base):
    """One row of the uploaded list. `token` is the personal link/QR printed
    on that person's invitation (/a/{slug}/i/{token}); when they respond,
    responded_letter_id ties the mailing to the story letter it produced."""
    __tablename__ = 'campaign_invitations'
    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey('prospect_campaigns.id'), nullable=False)
    advisor_email = Column(String, nullable=False)
    token = Column(String, unique=True, nullable=False)
    full_name = Column(String, nullable=False)
    first_name = Column(String)
    line1 = Column(String, nullable=False)
    line2 = Column(String)
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)
    zip_code = Column(String, nullable=False)
    status = Column(String, default='pending')   # pending | sent | failed | skipped
    skip_reason = Column(String)
    postgrid_id = Column(String)
    error = Column(Text)
    sent_at = Column(DateTime)
    responded_letter_id = Column(Integer)
    responded_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class ProspectCreditLedger(Base):
    """Letter balance per advisor = SUM(delta). A ledger (not a counter) so
    every purchase, grant and consumption is auditable. The first-campaign
    price applies when the advisor has no prior 'purchase' row."""
    __tablename__ = 'prospect_credit_ledger'
    id = Column(Integer, primary_key=True, autoincrement=True)
    advisor_email = Column(String, nullable=False)
    delta = Column(Integer, nullable=False)
    reason = Column(String)              # purchase | grant | consume | refund
    reference = Column(String)           # stripe session id / letter id / admin email
    created_at = Column(DateTime, default=datetime.utcnow)


class DncSuppression(Base):
    """Internal do-not-call list: opt-outs, complaints, wrong numbers.
    Checked before EVERY dial, in addition to any external provider."""
    __tablename__ = 'dnc_suppressions'
    id = Column(Integer, primary_key=True, autoincrement=True)
    phone = Column(String, unique=True, nullable=False)   # E.164
    reason = Column(String)
    added_by = Column(String)
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
                    # Firm lookup: the advisor's CURRENT profile first (where
                    # firm branding is actually edited), then the legacy
                    # advisors table, then whatever the heir profile carries.
                    firm = None
                    adv_profile = session.query(UserProfile).filter_by(email=client.advisor_email).first()
                    if adv_profile and adv_profile.advisor_firm:
                        firm = adv_profile.advisor_firm
                    if not firm:
                        adv = session.query(Advisor).filter_by(email=client.advisor_email).first()
                        firm = adv.firm_name if adv else None
                    if not firm:
                        firm = p.get("advisor_firm") or "VerbaPost"
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
def create_sponsored_user(advisor_email, client_name, client_email, client_phone, advisor_firm=None):
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
                "advisor_firm": advisor_firm or "VerbaPost"  # sponsoring firm's branding
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
# 🆕 RECIPIENT ADDRESS BOOK (multi-letter mailing)
# ==========================================

MAX_EXTRA_RECIPIENTS = 4  # heir's own address + 4 = 5 letters per story


def get_recipients(user_email):
    try:
        with get_db_session() as session:
            rows = (session.query(Recipient)
                    .filter_by(user_email=user_email.strip().lower())
                    .order_by(Recipient.created_at).limit(MAX_EXTRA_RECIPIENTS).all())
            return [to_dict(r) for r in rows]
    except Exception:
        return []


def add_recipient(user_email, name, street, city, state, zip_code):
    user_email = user_email.strip().lower()
    try:
        with get_db_session() as session:
            count = session.query(Recipient).filter_by(user_email=user_email).count()
            if count >= MAX_EXTRA_RECIPIENTS:
                return False, f"Limit reached ({MAX_EXTRA_RECIPIENTS} additional recipients)."
            session.add(Recipient(user_email=user_email, name=name.strip(),
                                  street=street.strip(), city=city.strip(),
                                  state=state.strip(), zip_code=zip_code.strip()))
            return True, "Added"
    except Exception as e:
        logger.error(f"Add recipient failed: {e}")
        return False, "Database error"


def delete_recipient(recipient_id, user_email):
    """Ownership enforced: users may only delete their own recipients."""
    try:
        with get_db_session() as session:
            r = (session.query(Recipient)
                 .filter_by(id=int(recipient_id), user_email=user_email.strip().lower())
                 .first())
            if not r:
                return False
            session.delete(r)
            return True
    except Exception:
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
                    "storyteller": proj.heir_name or "Family Member",
                    # B2B projects: public playback requires advisor release
                    "released": bool(proj.audio_released)
                }

            # 2. Check LETTER_DRAFT table (Legacy/B2C)
            draft = db.query(LetterDraft).filter(LetterDraft.id == safe_id).first()
            if draft:
                return {
                    "id": draft.id,
                    "url": draft.tracking_number,
                    "title": f"Story #{draft.id}",
                    "date": draft.created_at.strftime("%B %d, %Y") if draft.created_at else "Unknown",
                    "storyteller": "Family Member",
                    # Legacy B2C drafts predate the advisor-release system;
                    # QR codes already mailed must keep working.
                    "released": True
                }
            return None
    except Exception as e:
        logger.error(f"Public Draft Fetch Error: {e}")
        return None

# ==========================================
# 🆕 PROSPECT ACQUISITION HELPERS
# ==========================================

from sqlalchemy import func as _sa_func

RESERVATION_WINDOW_HOURS = 24   # an unanswered intake stops holding a letter after this


def get_advisor_page_by_email(advisor_email):
    try:
        with get_db_session() as session:
            row = session.query(AdvisorPage).filter_by(advisor_email=advisor_email.strip().lower()).first()
            return to_dict(row) if row else None
    except Exception as e:
        logger.error(f"Advisor page lookup failed: {e}")
        return None


def get_advisor_page_by_slug(slug):
    try:
        with get_db_session() as session:
            row = session.query(AdvisorPage).filter_by(slug=(slug or "").strip().lower()).first()
            return to_dict(row) if row else None
    except Exception as e:
        logger.error(f"Advisor page slug lookup failed: {e}")
        return None


def upsert_advisor_page(advisor_email, **fields):
    """Create or update the advisor's landing page. Returns (ok, message).
    Slug uniqueness is enforced here so two advisors can never share a URL."""
    advisor_email = advisor_email.strip().lower()
    try:
        with get_db_session() as session:
            slug = (fields.get("slug") or "").strip().lower()
            if slug:
                clash = session.query(AdvisorPage).filter(
                    AdvisorPage.slug == slug, AdvisorPage.advisor_email != advisor_email).first()
                if clash:
                    return False, "That page address is already taken."
            row = session.query(AdvisorPage).filter_by(advisor_email=advisor_email).first()
            if not row:
                if not slug or not fields.get("display_name"):
                    return False, "A page address and display name are required."
                row = AdvisorPage(advisor_email=advisor_email, slug=slug,
                                  display_name=fields.get("display_name"))
                session.add(row)
            for k, v in fields.items():
                if k in ("id", "advisor_email", "created_at"):
                    continue
                if v is None:
                    continue
                if hasattr(row, k):
                    setattr(row, k, v)
            return True, "Saved"
    except Exception as e:
        logger.error(f"Advisor page upsert failed: {e}")
        return False, "Database error"


# --- letter balance (ledger) ---

def prospect_credit_balance(advisor_email):
    try:
        with get_db_session() as session:
            total = session.query(_sa_func.coalesce(_sa_func.sum(ProspectCreditLedger.delta), 0)) \
                .filter(ProspectCreditLedger.advisor_email == advisor_email.strip().lower()).scalar()
            return int(total or 0)
    except Exception as e:
        logger.error(f"Prospect balance failed: {e}")
        return 0


def prospect_has_prior_purchase(advisor_email):
    """True once the advisor has bought ANY campaign — repeat pricing applies."""
    try:
        with get_db_session() as session:
            return session.query(ProspectCreditLedger).filter_by(
                advisor_email=advisor_email.strip().lower(), reason="purchase").first() is not None
    except Exception:
        return False


def add_prospect_credits(advisor_email, delta, reason, reference=None):
    try:
        with get_db_session() as session:
            session.add(ProspectCreditLedger(advisor_email=advisor_email.strip().lower(),
                                             delta=int(delta), reason=reason, reference=reference))
            return True
    except Exception as e:
        logger.error(f"Prospect ledger write failed: {e}")
        return False


def prospect_open_reservations(advisor_email):
    """Intakes that have consented / are being called but have no recording yet.
    They hold a letter for RESERVATION_WINDOW_HOURS so the page can't oversell."""
    try:
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=RESERVATION_WINDOW_HOURS)
        with get_db_session() as session:
            return session.query(ProspectLetter).filter(
                ProspectLetter.advisor_email == advisor_email.strip().lower(),
                ProspectLetter.status.in_(("consented", "calling")),
                ProspectLetter.created_at >= cutoff).count()
    except Exception:
        return 0


def prospect_story_allowance(advisor_email):
    """Every invitation the advisor has bought (or been granted) includes ONE
    story letter. Allowance = all positive ledger entries - story letters
    already produced - intakes still in flight. This is what gates the
    landing page, so a link shared on social media can't run up unlimited
    Twilio + linen costs on a $500 campaign."""
    email = advisor_email.strip().lower()
    try:
        with get_db_session() as session:
            bought = session.query(_sa_func.coalesce(_sa_func.sum(ProspectCreditLedger.delta), 0)) \
                .filter(ProspectCreditLedger.advisor_email == email,
                        ProspectCreditLedger.delta > 0).scalar() or 0
            produced = session.query(ProspectLetter).filter(
                ProspectLetter.advisor_email == email,
                ProspectLetter.status.in_(("recorded", "Approved", "Sent"))).count()
        return int(bought) - int(produced) - prospect_open_reservations(email)
    except Exception as e:
        logger.error(f"Story allowance failed: {e}")
        return 0


def prospect_letters_available(advisor_email):
    """Landing-page gate (name kept for the router). Story letters are
    included with invitations, so this is the story allowance, not the
    invitation balance."""
    return prospect_story_allowance(advisor_email)


# --- the send log ---

def create_prospect_letter(**fields):
    try:
        with get_db_session() as session:
            row = ProspectLetter(**fields)
            session.add(row)
            session.flush()
            return row.id
    except Exception as e:
        logger.error(f"Create prospect letter failed: {e}")
        return None


def get_prospect_letter(letter_id):
    try:
        with get_db_session() as session:
            row = session.query(ProspectLetter).filter_by(id=int(letter_id)).first()
            return to_dict(row) if row else None
    except Exception:
        return None


def update_prospect_letter(letter_id, **fields):
    try:
        with get_db_session() as session:
            row = session.query(ProspectLetter).filter_by(id=int(letter_id)).first()
            if not row:
                return False
            for k, v in fields.items():
                if hasattr(row, k):
                    setattr(row, k, v)
            return True
    except Exception as e:
        logger.error(f"Update prospect letter failed: {e}")
        return False


def find_recent_prospect_by_phone(advisor_email, phone_e164, days=90):
    """Dedupe: one free letter per phone per advisor per 90 days."""
    try:
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)
        with get_db_session() as session:
            row = session.query(ProspectLetter).filter(
                ProspectLetter.advisor_email == advisor_email.strip().lower(),
                ProspectLetter.prospect_phone == phone_e164,
                ProspectLetter.created_at >= cutoff,
                ProspectLetter.status != "dnc_blocked").first()
            return to_dict(row) if row else None
    except Exception:
        return None


def update_prospect_by_sid(call_sid, transcript, audio_url):
    """Recording arrived for a prospect call. Returns the letter id or None.
    Only attaches to rows still waiting (status 'calling') so a duplicate
    Twilio callback can never overwrite a finished letter."""
    try:
        with get_db_session() as session:
            row = session.query(ProspectLetter).filter_by(call_sid=call_sid).first()
            if not row:
                return None
            if row.status != "calling":
                return row.id
            row.transcript_raw = transcript
            row.audio_url = audio_url
            row.status = "recorded"
            return row.id
    except Exception as e:
        logger.error(f"Update prospect by SID failed: {e}")
        return None


def list_prospect_letters(advisor_email=None, statuses=None):
    try:
        with get_db_session() as session:
            q = session.query(ProspectLetter)
            if advisor_email:
                q = q.filter(ProspectLetter.advisor_email == advisor_email.strip().lower())
            if statuses:
                q = q.filter(ProspectLetter.status.in_(statuses))
            return [to_dict(r) for r in q.order_by(ProspectLetter.created_at.desc()).all()]
    except Exception as e:
        logger.error(f"List prospect letters failed: {e}")
        return []


# --- internal DNC list ---

def is_dnc_suppressed(phone_e164):
    try:
        with get_db_session() as session:
            return session.query(DncSuppression).filter_by(phone=phone_e164).first() is not None
    except Exception as e:
        # Unknown state is NOT "clear" — the caller decides how to treat errors.
        logger.error(f"DNC lookup failed: {e}")
        raise


def add_dnc_suppression(phone_e164, reason="opt-out", added_by="system"):
    try:
        with get_db_session() as session:
            if session.query(DncSuppression).filter_by(phone=phone_e164).first():
                return True
            session.add(DncSuppression(phone=phone_e164, reason=reason, added_by=added_by))
            return True
    except Exception as e:
        logger.error(f"DNC add failed: {e}")
        return False


# ==========================================
# 🆕 INVITATION CAMPAIGNS (uploaded mailing list -> PostGrid)
# ==========================================

import secrets as _secrets


def _invite_token():
    """URL-safe, but never starting with '-' or '_': a leading dash makes the
    token look like a formula to Excel (the CSV export escapes it) and reads
    badly when a prospect types the link off the printed letter."""
    while True:
        t = _secrets.token_urlsafe(8)
        if t[0].isalnum():
            return t


def create_campaign(advisor_email, page_id, name, rows):
    """rows: list of dicts {full_name, first_name, line1, line2, city, state, zip_code}.
    Every row gets a unique personal token. Returns campaign id or None."""
    advisor_email = advisor_email.strip().lower()
    try:
        with get_db_session() as session:
            camp = ProspectCampaign(advisor_email=advisor_email, page_id=page_id, name=name,
                                    status="draft", total_rows=len(rows))
            session.add(camp)
            session.flush()
            for r in rows:
                session.add(CampaignInvitation(
                    campaign_id=camp.id, advisor_email=advisor_email,
                    token=_invite_token(),
                    full_name=r["full_name"], first_name=r.get("first_name"),
                    line1=r["line1"], line2=r.get("line2"), city=r["city"],
                    state=r["state"], zip_code=r["zip_code"], status="pending"))
            session.flush()
            return camp.id
    except Exception as e:
        logger.error(f"Create campaign failed: {e}")
        return None


def get_campaign(campaign_id, advisor_email=None):
    try:
        with get_db_session() as session:
            q = session.query(ProspectCampaign).filter_by(id=int(campaign_id))
            if advisor_email:
                q = q.filter_by(advisor_email=advisor_email.strip().lower())
            row = q.first()
            return to_dict(row) if row else None
    except Exception:
        return None


def list_campaigns(advisor_email):
    try:
        with get_db_session() as session:
            rows = session.query(ProspectCampaign).filter_by(
                advisor_email=advisor_email.strip().lower()).order_by(ProspectCampaign.created_at.desc()).all()
            return [to_dict(r) for r in rows]
    except Exception:
        return []


def update_campaign(campaign_id, **fields):
    try:
        with get_db_session() as session:
            row = session.query(ProspectCampaign).filter_by(id=int(campaign_id)).first()
            if not row:
                return False
            for k, v in fields.items():
                if hasattr(row, k):
                    setattr(row, k, v)
            return True
    except Exception as e:
        logger.error(f"Update campaign failed: {e}")
        return False


def list_invitations(campaign_id=None, advisor_email=None, statuses=None):
    try:
        with get_db_session() as session:
            q = session.query(CampaignInvitation)
            if campaign_id is not None:
                q = q.filter(CampaignInvitation.campaign_id == int(campaign_id))
            if advisor_email:
                q = q.filter(CampaignInvitation.advisor_email == advisor_email.strip().lower())
            if statuses:
                q = q.filter(CampaignInvitation.status.in_(statuses))
            return [to_dict(r) for r in q.order_by(CampaignInvitation.id).all()]
    except Exception as e:
        logger.error(f"List invitations failed: {e}")
        return []


def get_invitation_by_token(token):
    if not token:
        return None
    try:
        with get_db_session() as session:
            row = session.query(CampaignInvitation).filter_by(token=str(token).strip()).first()
            return to_dict(row) if row else None
    except Exception:
        return None


def update_invitation(invitation_id, **fields):
    try:
        with get_db_session() as session:
            row = session.query(CampaignInvitation).filter_by(id=int(invitation_id)).first()
            if not row:
                return False
            for k, v in fields.items():
                if hasattr(row, k):
                    setattr(row, k, v)
            return True
    except Exception as e:
        logger.error(f"Update invitation failed: {e}")
        return False


def previously_mailed_addresses(advisor_email):
    """Set of normalized (line1, zip5) already SENT by this advisor — so a
    re-uploaded list doesn't mail the same household twice."""
    try:
        with get_db_session() as session:
            rows = session.query(CampaignInvitation.line1, CampaignInvitation.zip_code).filter(
                CampaignInvitation.advisor_email == advisor_email.strip().lower(),
                CampaignInvitation.status == "sent").all()
            return {(l.strip().lower(), (z or "")[:5]) for l, z in rows if l}
    except Exception:
        return set()


def mark_invitation_responded(invitation_id, letter_id):
    try:
        with get_db_session() as session:
            row = session.query(CampaignInvitation).filter_by(id=int(invitation_id)).first()
            if not row:
                return False
            if row.responded_letter_id is None:
                row.responded_letter_id = int(letter_id)
                row.responded_at = datetime.utcnow()
            return True
    except Exception as e:
        logger.error(f"Mark responded failed: {e}")
        return False
