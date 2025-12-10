import streamlit as st
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import json
import secrets_manager
from contextlib import contextmanager
import logging

# --- CONFIG ---
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
    user_email = Column(String, index=True) 
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
    current_uses = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

# --- ENGINE ---
@st.cache_resource
def get_engine():
    db_url = secrets_manager.get_secret("DATABASE_URL")
    if db_url:
        db_url = db_url.replace("postgres://", "postgresql://")
    else:
        db_url = "sqlite:///local_dev.db"
        
    try:
        # pool_pre_ping checks connections before using them (prevents stale connection errors)
        engine = create_engine(db_url, pool_pre_ping=True)
        Base.metadata.create_all(bind=engine)
        return engine
    except Exception as e:
        logger.error(f"DB Error: {e}")
        return None

# --- CONTEXT MANAGER (The Fix) ---
@contextmanager
def get_db_session():
    """
    Provides a transactional scope around a series of operations.
    Automatically commits on success, rollbacks on error, and closes always.
    """
    engine = get_engine()
    if not engine:
        raise RuntimeError("Database engine could not be initialized")
        
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

# --- CORE FUNCTIONS ---

def get_user_profile(email):
    try:
        with get_db_session() as db:
            return db.query(UserProfile).filter(UserProfile.email == email).first()
    except Exception:
        return None

def save_draft(email, text, tier, price, to_addr=None, from_addr=None, sig_data=None, status="Draft"):
    try:
        with get_db_session() as db:
            r_json = json.dumps(to_addr) if to_addr else "{}"
            s_json = json.dumps(from_addr) if from_addr else "{}"
            
            draft = LetterDraft(
                user_email=email, transcription=text, tier=tier, price=str(price), status=status,
                recipient_json=r_json, sender_json=s_json, signature_data=str(sig_data) if sig_data else None
            )
            db.add(draft)
            # Flush sends SQL to DB to generate ID without closing transaction yet
            db.flush() 
            db.refresh(draft)
            return draft.id
    except Exception as e:
        logger.error(f"Save Draft Error: {e}")
        return None

def update_draft_data(draft_id, to_addr=None, from_addr=None, content=None, status=None, tier=None, price=None):
    try:
        with get_db_session() as db:
            draft = db.query(LetterDraft).filter(LetterDraft.id == draft_id).first()
            if draft:
                if to_addr: draft.recipient_json = json.dumps(to_addr)
                if from_addr: draft.sender_json = json.dumps(from_addr)
                if content: draft.transcription = content
                if status: draft.status = status
                if tier: draft.tier = tier
                if price: draft.price = str(price)
                return True
            return False
    except Exception as e:
        logger.error(f"Update Draft Error: {e}")
        return False

def update_user_profile(email, name, street, street2, city, state, zip_code, country="US"):
    try:
        with get_db_session() as db:
            user = db.query(UserProfile).filter(UserProfile.email == email).first()
            if user:
                user.full_name = name; user.address_line1 = street; user.address_line2 = street2
                user.address_city = city; user.address_state = state; user.address_zip = zip_code
                user.country = country
                # Commit handled by context manager
    except Exception as e:
        logger.error(f"Update Profile Error: {e}")

def fetch_all_drafts():
    try:
        with get_db_session() as db:
            results = db.query(LetterDraft).order_by(LetterDraft.created_at.desc()).all()
            data = []
            for r in results:
                data.append({
                    "ID": r.id, "Email": r.user_email, "Tier": r.tier, "Status": r.status,
                    "Date": r.created_at, "Price": r.price, "Content": r.transcription,
                    "Recipient": r.recipient_json, "Sender": r.sender_json, "Signature": r.signature_data
                })
            return data
    except Exception as e:
        logger.error(f"Fetch Drafts Error: {e}")
        return []

# --- ADDRESS BOOK ---

def add_contact(user_email, name, street, street2, city, state, zip_code, country="US"):
    try:
        with get_db_session() as db:
            exists = db.query(SavedContact).filter(SavedContact.user_email == user_email, SavedContact.name == name).first()
            if exists:
                exists.street = street; exists.street2 = street2; exists.city = city
                exists.state = state; exists.zip_code = zip_code; exists.country = country
            else:
                contact = SavedContact(
                    user_email=user_email, name=name, street=street, street2=street2,
                    city=city, state=state, zip_code=zip_code, country=country
                )
                db.add(contact)
            return True
    except Exception as e:
        logger.error(f"Add Contact Error: {e}")
        return False

def get_contacts(user_email):
    try:
        with get_db_session() as db:
            return db.query(SavedContact).filter(SavedContact.user_email == user_email).order_by(SavedContact.name).all()
    except Exception:
        return []

def delete_contact(contact_id):
    try:
        with get_db_session() as db:
            db.query(SavedContact).filter(SavedContact.id == contact_id).delete()
            return True
    except Exception:
        return False

# --- GAMIFICATION ---
def get_civic_leaderboard():
    try:
        with get_db_session() as db:
            results = db.query(LetterDraft).filter(
                LetterDraft.tier == 'Civic',
                LetterDraft.status.in_(['Completed', 'Pending Admin'])
            ).order_by(LetterDraft.created_at.desc()).limit(500).all()
            
            state_counts = {}
            for r in results:
                try:
                    if r.recipient_json:
                        data = json.loads(r.recipient_json)
                        state = data.get('state', '').upper()
                        if state and len(state) == 2:
                            state_counts[state] = state_counts.get(state, 0) + 1
                except: continue
                    
            sorted_stats = sorted(state_counts.items(), key=lambda item: item[1], reverse=True)
            return sorted_stats[:5]
    except Exception as e:
        logger.error(f"Leaderboard Error: {e}")
        return []