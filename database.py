import streamlit as st
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import json
import secrets_manager
from contextlib import contextmanager
import logging
import numpy as np

# --- CONFIG ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
Base = declarative_base()

# --- MODELS ---
class UserProfile(Base):
    __tablename__ = "user_profiles"
    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    address_line1 = Column(String)
    address_line2 = Column(String, nullable=True) 
    address_city = Column(String)
    address_state = Column(String)
    address_zip = Column(String)
    country = Column(String, default="US")
    created_at = Column(DateTime, default=datetime.utcnow)
    language_preference = Column(String, default="English")

class LetterDraft(Base):
    __tablename__ = "letter_drafts"
    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, index=True)
    transcription = Column(Text)
    status = Column(String, default="Draft") 
    tier = Column(String)
    price = Column(String)
    recipient_json = Column(Text)
    sender_json = Column(Text)
    signature_data = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class SavedContact(Base):
    __tablename__ = "saved_contacts"
    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, index=True, nullable=False)
    name = Column(String)
    street = Column(String)
    street2 = Column(String, nullable=True) 
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)
    country = Column(String, default="US")
    created_at = Column(DateTime, default=datetime.utcnow)

class PromoCode(Base):
    __tablename__ = "promo_codes"
    code = Column(String, primary_key=True, index=True)
    max_uses = Column(Integer, default=1)
    # Replaces 'current_uses' with 'active' to match your DB schema
    active = Column(Boolean, default=True) 
    created_at = Column(DateTime, default=datetime.utcnow)

class PromoLog(Base):
    __tablename__ = "promo_logs"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, index=True)
    user_email = Column(String)
    used_at = Column(DateTime, default=datetime.utcnow)

# --- ENGINE ---
@st.cache_resource
def get_engine():
    db_url = secrets_manager.get_secret("DATABASE_URL")
    if not db_url:
        try: db_url = st.secrets.get("DATABASE_URL")
        except: pass

    if db_url:
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://")
    else:
        db_url = "sqlite:///local_dev.db"
        
    try:
        engine = create_engine(db_url, pool_pre_ping=True)
        Base.metadata.create_all(bind=engine)
        return engine
    except Exception as e:
        logger.error(f"DB Connection Error: {e}")
        return None

# --- CONTEXT MANAGER ---
@contextmanager
def get_db_session():
    engine = get_engine()
    if not engine: raise RuntimeError("Database engine could not be initialized")
    session = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

# --- HELPER: SAFE INT CONVERSION ---
def _safe_int(val):
    if val is None: return None
    if isinstance(val, (np.integer, np.int64)):
        return int(val)
    return val

# --- CORE FUNCTIONS ---
def get_user_profile(email):
    if not email: return None
    try:
        with get_db_session() as db:
            return db.query(UserProfile).filter(UserProfile.email == email).first()
    except Exception: return None

def save_draft(email, text, tier, price, to_addr=None, from_addr=None, sig_data=None, status="Draft"):
    try:
        with get_db_session() as db:
            r_json = json.dumps(to_addr) if to_addr else "{}"
            s_json = json.dumps(from_addr) if from_addr else "{}"
            draft = LetterDraft(user_email=email, transcription=text, tier=tier, price=str(price), status=status, recipient_json=r_json, sender_json=s_json, signature_data=str(sig_data) if sig_data else None)
            db.add(draft)
            db.flush(); db.refresh(draft)
            return draft.id
    except Exception as e: logger.error(f"Save Draft Error: {e}"); return None

def update_draft_data(draft_id, to_addr=None, from_addr=None, content=None, status=None, tier=None, price=None):
    try:
        safe_id = _safe_int(draft_id)
        with get_db_session() as db:
            draft = db.query(LetterDraft).filter(LetterDraft.id == safe_id).first()
            if draft:
                if to_addr: draft.recipient_json = json.dumps(to_addr)
                if from_addr: draft.sender_json = json.dumps(from_addr)
                if content: draft.transcription = content
                if status: draft.status = status
                if tier: draft.tier = tier
                if price: draft.price = str(price)
                return True
            return False
    except Exception as e: logger.error(f"Update Draft Error: {e}"); return False

def update_user_profile(email, name, street, street2, city, state, zip_code, country="US"):
    if not email: return
    try:
        with get_db_session() as db:
            user = db.query(UserProfile).filter(UserProfile.email == email).first()
            if user:
                user.full_name = name; user.address_line1 = street; user.address_line2 = street2
                user.address_city = city; user.address_state = state; user.address_zip = zip_code
                user.country = country
    except Exception as e: logger.error(f"Update Profile Error: {e}")

# --- ADDRESS BOOK ---
def add_contact(user_email, name, street, street2, city, state, zip_code, country="US"):
    if not user_email: return False
    try:
        with get_db_session() as db:
            exists = db.query(SavedContact).filter(SavedContact.user_email == user_email, SavedContact.name == name).first()
            if exists:
                exists.street = street; exists.street2 = street2; exists.city = city
                exists.state = state; exists.zip_code = zip_code; exists.country = country
            else:
                contact = SavedContact(user_email=user_email, name=name, street=street, street2=street2, city=city, state=state, zip_code=zip_code, country=country)
                db.add(contact)
            return True
    except Exception as e: logger.error(f"Add Contact Error: {e}"); return False

def get_contacts(user_email):
    if not user_email: return []
    try:
        with get_db_session() as db:
            return db.query(SavedContact).filter(SavedContact.user_email == user_email).order_by(SavedContact.name).all()
    except Exception: return []

def delete_contact(contact_id):
    try:
        safe_id = _safe_int(contact_id)
        with get_db_session() as db:
            db.query(SavedContact).filter(SavedContact.id == safe_id).delete()
            return True
    except Exception: return False

# --- DELETE DRAFT ---
def delete_draft(draft_id):
    try:
        safe_id = _safe_int(draft_id)
        with get_db_session() as db:
            db.query(LetterDraft).filter(LetterDraft.id == safe_id).delete()
            return True
    except Exception as e:
        logger.error(f"Delete Draft Error: {e}")
        return False

# --- ADMIN SUPPORT ---
def get_civic_leaderboard():
    try:
        with get_db_session() as db:
            drafts = db.query(LetterDraft).filter(LetterDraft.tier == 'Civic', LetterDraft.status.in_(['Completed', 'PAID'])).all()
            counts = {}
            for d in drafts:
                try:
                    if d.recipient_json:
                        data = json.loads(d.recipient_json)
                        state = (data.get('state') or data.get('address_state') or data.get('provinceOrState'))
                        if state:
                            st_norm = state.strip().upper()[:2] 
                            counts[st_norm] = counts.get(st_norm, 0) + 1
                except: continue
            return sorted(counts.items(), key=lambda x: x[1], reverse=True)[:5]
    except Exception as e: logger.error(f"Leaderboard Error: {e}"); return []

def fetch_all_drafts():
    try:
        with get_db_session() as db:
            drafts = db.query(LetterDraft).order_by(LetterDraft.created_at.desc()).limit(100).all()
            results = []
            for d in drafts:
                results.append({
                    "ID": d.id, "Date": d.created_at.strftime("%Y-%m-%d %H:%M"),
                    "Email": d.user_email, "Tier": d.tier, "Status": d.status,
                    "Price": d.price, "Content": d.transcription,
                    "Recipient": d.recipient_json, "Sender": d.sender_json
                })
            return results
    except Exception as e: logger.error(f"Fetch Drafts Error: {e}"); return []