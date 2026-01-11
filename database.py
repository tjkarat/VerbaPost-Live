import os
import streamlit as st
import logging
import urllib.parse
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, Float, DateTime, BigInteger, Date, func
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from contextlib import contextmanager
from datetime import datetime, timedelta

# --- IMPORT SECRETS ---
try: import secrets_manager
except ImportError: secrets_manager = None

# --- CONFIGURATION ---
logger = logging.getLogger(__name__)
Base = declarative_base()

# Global variables for Lazy Loading
_engine = None
_SessionLocal = None

def get_db_url():
    """
    Refactored to use secrets_manager for consistent lookup
    across Dev (Streamlit Cloud) and Prod (Google Cloud Run).
    """
    if not secrets_manager:
        logger.error("Secrets Manager module missing")
        return None

    try:
        # 1. Try standard connection string first (Prod/Env Var)
        url = secrets_manager.get_secret("DATABASE_URL")
        if url: return url

        # 2. Try Supabase specific keys (QA/Streamlit Secrets)
        sb_url = secrets_manager.get_secret("supabase.url")
        sb_key = secrets_manager.get_secret("supabase.key")
        sb_pass = secrets_manager.get_secret("supabase.db_password") or sb_key

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
    data = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
    
    # Auto-fill address_line1 if street exists
    if 'street' in data and 'address_line1' not in data:
        data['address_line1'] = data['street']
    
    # Auto-fill zip_code if zip exists
    if 'zip' in data and 'zip_code' not in data:
        data['zip_code'] = data['zip']
        
    return data

# ==========================================
# 🏛️ MODELS
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
    # --- ADDED FOR B2B PIVOT ---
    role = Column(String, default="user") # 'user', 'partner', 'admin'

class PromoLog(Base):
    __tablename__ = 'promo_logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, index=True)
    user_email = Column(String)
    used_at = Column(DateTime, default=datetime.utcnow)

class AuditEvent(Base):
    __tablename__ = 'audit_events'
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_email = Column(String)
    event_type = Column(String)
    details = Column(Text)
    description = Column(Text)
    stripe_session_id = Column(String)

class LetterDraft(Base):
    __tablename__ = 'letter_drafts'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_email = Column(String)
    content = Column(Text)
    status = Column(String, default="Draft")
    tier = Column(String, default="Heirloom") 
    price = Column(Float, default=0.0)
    tracking_number = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    to_addr = Column(Text)
    from_addr = Column(Text)
    audio_ref = Column(Text)
    recipient_data = Column(Text) 
    sender_data = Column(Text)

class ScheduledEvent(Base):
    __tablename__ = 'scheduled_events'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_email = Column(String, nullable=False)
    recipient_json = Column(JSONB, nullable=False) 
    event_date = Column(Date, nullable=False)      
    event_type = Column(String)
    recurrence = Column(String)
    status = Column(String, default="Active")
    audio_url = Column(String)
    ai_prompt = Column(String)

class Letter(Base):
    __tablename__ = 'letters'
    id = Column(Integer, primary_key=True, autoincrement=True) 
    user_id = Column(Integer)
    content = Column(Text)
    status = Column(String) 
    recipient_name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    user_email = Column(String, nullable=True) 
    recipient_data = Column(Text)
    sender_data = Column(Text)
    
class Contact(Base):
    __tablename__ = 'saved_contacts'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_email = Column(String)
    name = Column(String)
    street = Column(String)
    street2 = Column(String, nullable=True)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)
    country = Column(String, default="US")
    zip = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class PromoCode(Base):
    __tablename__ = 'promo_codes'
    code = Column(String, primary_key=True)
    active = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    max_uses = Column(BigInteger)
    discount_amount = Column(Float, default=0.0)
    current_uses = Column(Integer, default=0)
    uses = Column(Integer, default=0)

class PaymentFulfillment(Base):
    __tablename__ = 'payment_fulfillments'
    id = Column(Integer, primary_key=True, autoincrement=True)
    stripe_session_id = Column(String, unique=True, nullable=False)
    status = Column(String, default="fulfilled")
    created_at = Column(DateTime, default=datetime.utcnow)

# ==========================================
# 🛠️ FUNCTIONS
# ==========================================

def update_subscription_state(email, sub_id, customer_id, period_end_dt, refill_credits=False):
    try:
        with get_db_session() as session:
            profile = session.query(UserProfile).filter_by(email=email).first()
            if profile:
                profile.stripe_subscription_id = sub_id
                profile.stripe_customer_id = customer_id
                profile.subscription_end_date = period_end_dt
                if refill_credits:
                    profile.credits = 4
                    logger.info(f"Credits refilled for {email}")
                session.commit()
                return True
            return False
    except Exception as e:
        logger.error(f"Update Subscription State Error: {e}")
        return False

# Backward compatibility alias
update_user_subscription_id = lambda e, s: update_subscription_state(e, s, None, None)

def get_all_orders():
    combined = []
    try:
        with get_db_session() as session:
            legacy = session.query(Letter).order_by(Letter.created_at.desc()).limit(50).all()
            for o in legacy:
                d = to_dict(o)
                if not d.get('user_email'): d['user_email'] = f"ID: {d.get('user_id', '?')}"
                d['source'] = 'Sent Letter'
                combined.append(d)
    except Exception as e:
        logger.error(f"Error fetching Letters table: {e}")

    try:
        with get_db_session() as session:
            heirloom = session.query(LetterDraft).order_by(LetterDraft.created_at.desc()).limit(50).all()
            for h in heirloom:
                d = to_dict(h)
                d['source'] = 'Draft/Heirloom'
                d['recipient_name'] = "Pending..."
                if 'tier' not in d or not d['tier']: d['tier'] = 'Heirloom'
                combined.append(d)
    except Exception as e:
        logger.error(f"Error fetching Drafts table: {e}")

    if combined:
        try: combined.sort(key=lambda x: x.get('created_at') or datetime.min, reverse=True)
        except: pass
        
    return combined[:100]

def get_all_users():
    try:
        with get_db_session() as session:
            users = session.query(UserProfile).all()
            results = []
            for u in users:
                d = to_dict(u)
                d['credits_remaining'] = d.get('credits', 0)
                # Ensure role exists in dict
                if 'role' not in d or not d['role']: d['role'] = 'user'
                results.append(d)
            return results
    except Exception as e:
        logger.error(f"Get Users Error: {e}")
        return []

def update_user_role(email, new_role):
    """
    Promotes or Demotes a user (e.g. 'user' -> 'partner').
    """
    try:
        with get_db_session() as session:
            profile = session.query(UserProfile).filter_by(email=email).first()
            if profile:
                profile.role = new_role
                session.commit()
                return True
            return False
    except Exception as e:
        logger.error(f"Update Role Error: {e}")
        return False

def get_all_promos():
    try:
        with get_db_session() as session:
            promos = session.query(PromoCode).all()
            return [to_dict(p) for p in promos]
    except Exception as e:
        logger.error(f"Get Promos Error: {e}")
        return []

def save_audit_log(log_entry):
    try:
        with get_db_session() as session:
            valid_keys = {'user_email', 'event_type', 'details', 'description', 'stripe_session_id'}
            filtered_entry = {k: v for k, v in log_entry.items() if k in valid_keys}
            log = AuditEvent(**filtered_entry)
            session.add(log)
            session.commit()
            return True
    except Exception as e:
        logger.error(f"Audit Save Error: {e}")
        return False

def get_audit_logs(limit=100):
    try:
        with get_db_session() as session:
            logs = session.query(AuditEvent).order_by(AuditEvent.timestamp.desc()).limit(limit).all()
            return [to_dict(l) for l in logs]
    except Exception as e:
        logger.error(f"Audit Log Fetch Error: {e}")
        return []

def get_user_profile(email):
    try:
        with get_db_session() as session:
            profile = session.query(UserProfile).filter_by(email=email).first()
            if not profile:
                profile = UserProfile(email=email, credits=0, role="user")
                session.add(profile)
                session.commit()
            return to_dict(profile)
    except Exception as e:
        logger.error(f"Get Profile Error: {e}")
        return {}

def create_user(email, full_name):
    try:
        with get_db_session() as db:
            user = UserProfile(email=email, full_name=full_name, role="user")
            db.add(user)
            db.commit()
            return True
    except Exception as e:
        logger.error(f"Create User Error: {e}")
        return False

def update_user_credits(email, new_credit_count):
    try:
        with get_db_session() as session:
            profile = session.query(UserProfile).filter_by(email=email).first()
            if profile:
                profile.credits = new_credit_count
                session.commit()
                return True
            return False
    except Exception: return False

def update_heirloom_settings(email, parent_name, parent_phone):
    try:
        with get_db_session() as session:
            profile = session.query(UserProfile).filter_by(email=email).first()
            if profile:
                profile.parent_name = parent_name
                profile.parent_phone = parent_phone
                session.commit()
                return True
            else:
                return False
    except Exception as e:
        st.error(f"❌ DATABASE ERROR: {e}") 
        return False

def update_user_address(email, name, street, city, state, zip_code):
    try:
        with get_db_session() as session:
            profile = session.query(UserProfile).filter_by(email=email).first()
            if profile:
                profile.full_name = name
                profile.address_line1 = street
                profile.address_city = city
                profile.address_state = state
                profile.address_zip = zip_code
                session.commit()
                return True
            else:
                return False
    except Exception as e:
        st.error(f"❌ DATABASE ERROR (Address): {e}") 
        return False

def check_call_limit(email):
    try:
        with get_db_session() as session:
            profile = session.query(UserProfile).filter_by(email=email).first()
            if not profile or not profile.last_call_date: return True, "OK"
            diff = datetime.utcnow() - profile.last_call_date
            if diff < timedelta(hours=24):
                hours_left = 24 - int(diff.total_seconds() / 3600)
                return False, f"Please wait {hours_left} hours."
            return True, "OK"
    except Exception: return True, "Error checking limit"

def update_last_call_timestamp(email):
    try:
        with get_db_session() as session:
            profile = session.query(UserProfile).filter_by(email=email).first()
            if profile:
                profile.last_call_date = datetime.utcnow()
                session.commit()
    except: pass

def schedule_call(email, parent_phone, topic, scheduled_dt):
    try:
        recipient_data = {"phone": parent_phone, "name": "Heirloom Contact", "email": email}
        with get_db_session() as session:
            new_event = ScheduledEvent(
                user_email=email,
                recipient_json=recipient_data,
                event_date=scheduled_dt, 
                event_type="Interview Reminder",
                ai_prompt=topic,
                status="Active"
            )
            session.add(new_event)
            session.commit()
            return True
    except Exception as e:
        print(f"❌ SCHEDULING ERROR: {e}") 
        return False

def save_draft(email, content, tier="Standard", price=0.0, audio_ref=None):
    try:
        with get_db_session() as session:
            draft = LetterDraft(
                user_email=email, 
                content=content, 
                tier=tier, 
                price=price, 
                status="Draft",
                audio_ref=audio_ref
            )
            session.add(draft)
            session.commit()
            return draft.id
    except Exception as e:
        logger.error(f"Save Draft Error: {e}")
        return None

def get_user_drafts(email):
    try:
        with get_db_session() as session:
            drafts = session.query(LetterDraft).filter_by(user_email=email).order_by(LetterDraft.created_at.desc()).all()
            return [to_dict(d) for d in drafts]
    except Exception: return []

def update_draft_data(draft_id, **kwargs):
    try:
        with get_db_session() as session:
            draft = None
            try:
                d_int = int(draft_id)
                draft = session.query(LetterDraft).filter_by(id=d_int).first()
            except: pass
            if not draft:
                draft = session.query(LetterDraft).filter_by(id=str(draft_id)).first()

            if draft:
                for key, val in kwargs.items():
                    if hasattr(draft, key):
                        setattr(draft, key, val)
                session.commit()
                return True
            return False
    except Exception: return False

def get_contacts(email):
    try:
        with get_db_session() as session:
            contacts = session.query(Contact).filter_by(user_email=email).all()
            return [to_dict(c) for c in contacts]
    except Exception: return []

def save_contact(user_email, contact_data):
    try:
        with get_db_session() as session:
            new_c = Contact(
                user_email=user_email,
                name=contact_data.get("name"),
                street=contact_data.get("street") or contact_data.get("address_line1"),
                street2=contact_data.get("street2") or contact_data.get("address_line2"),
                city=contact_data.get("city"),
                state=contact_data.get("state"),
                zip_code=contact_data.get("zip_code") or contact_data.get("zip"),
                zip=contact_data.get("zip") or contact_data.get("zip_code"),
                country=contact_data.get("country", "US"),
                created_at=datetime.utcnow()
            )
            session.add(new_c)
            session.commit()
            return True
    except Exception as e:
        logger.error(f"Save Contact Error: {e}")
        return False

def delete_contact(user_email, contact_id):
    try:
        with get_db_session() as session:
            contact = session.query(Contact).filter_by(user_email=user_email, id=contact_id).first()
            if contact:
                session.delete(contact)
                session.commit()
                return True
            return False
    except Exception as e:
        logger.error(f"Delete Contact Error: {e}")
        return False

def create_promo_code(code, amount):
    try:
        with get_db_session() as db:
            p = PromoCode(code=code, discount_amount=amount, active=True, is_active=True)
            db.add(p)
            db.commit()
            return True
    except Exception: return False

def record_stripe_fulfillment(session_id):
    if not session_id: return False
    try:
        with get_db_session() as session:
            exists = session.query(PaymentFulfillment).filter_by(stripe_session_id=session_id).first()
            if exists: return False
            new_record = PaymentFulfillment(stripe_session_id=session_id)
            session.add(new_record)
            session.commit()
            return True
    except Exception as e:
        logger.error(f"Idempotency Check Error: {e}")
        return False

def is_fulfillment_recorded(session_id):
    if not session_id: return False
    try:
        with get_db_session() as session:
             exists = session.query(PaymentFulfillment).filter_by(stripe_session_id=session_id).first()
             return exists is not None
    except Exception as e:
        logger.error(f"Read Fulfillment Error: {e}")
        return True

def record_promo_usage(code, user_email):
    if not code: return False
    try:
        with get_db_session() as session:
            promo = session.query(PromoCode).filter_by(code=code).first()
            if promo:
                if hasattr(promo, 'current_uses'):
                    promo.current_uses = (promo.current_uses or 0) + 1
                if hasattr(promo, 'uses'):
                    promo.uses = (promo.uses or 0) + 1
            log = PromoLog(code=code, user_email=user_email, used_at=datetime.utcnow())
            session.add(log)
            session.commit()
            return True
    except Exception as e:
        logger.error(f"Record Promo Usage Error: {e}")
        return False