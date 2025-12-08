import streamlit as st
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, func
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import json
import secrets_manager

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
        engine = create_engine(db_url, pool_pre_ping=True)
        Base.metadata.create_all(bind=engine)
        return engine
    except Exception as e:
        print(f"DB Error: {e}")
        return None

def get_session():
    engine = get_engine()
    if not engine: return None
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()

# --- CORE FUNCTIONS ---
def get_user_profile(email):
    db = get_session()
    if not db: return None
    try: return db.query(UserProfile).filter(UserProfile.email == email).first()
    except: return None
    finally: db.close()

def save_draft(email, text, tier, price, to_addr=None, from_addr=None, sig_data=None, status="Draft"):
    db = get_session()
    if not db: return None
    try:
        r_json = json.dumps(to_addr) if to_addr else "{}"
        s_json = json.dumps(from_addr) if from_addr else "{}"
        
        draft = LetterDraft(
            user_email=email, transcription=text, tier=tier, price=str(price), status=status,
            recipient_json=r_json, sender_json=s_json, signature_data=str(sig_data) if sig_data else None
        )
        db.add(draft); db.commit(); db.refresh(draft)
        return draft.id
    except Exception as e:
        print(f"Save Error: {e}")
        db.rollback(); return None
    finally: db.close()

def update_draft_data(draft_id, to_addr=None, from_addr=None, content=None, status=None, tier=None, price=None):
    db = get_session()
    if not db: return False
    try:
        draft = db.query(LetterDraft).filter(LetterDraft.id == draft_id).first()
        if draft:
            if to_addr: draft.recipient_json = json.dumps(to_addr)
            if from_addr: draft.sender_json = json.dumps(from_addr)
            if content: draft.transcription = content
            if status: draft.status = status
            # --- FIX: Update Financials ---
            if tier: draft.tier = tier
            if price: draft.price = str(price)
            
            db.commit()
            return True
        return False
    except Exception as e:
        print(f"Update Error: {e}")
        db.rollback(); return False
    finally: db.close()

def update_user_profile(email, name, street, street2, city, state, zip_code, country="US"):
    db = get_session()
    if not db: return
    try:
        user = db.query(UserProfile).filter(UserProfile.email == email).first()
        if user:
            user.full_name = name; user.address_line1 = street; user.address_line2 = street2
            user.address_city = city; user.address_state = state; user.address_zip = zip_code
            user.country = country
            db.commit()
    except: pass
    finally: db.close()

def fetch_all_drafts():
    db = get_session()
    if not db: return []
    try:
        results = db.query(LetterDraft).order_by(LetterDraft.created_at.desc()).all()
        data = []
        for r in results:
            data.append({
                "ID": r.id, "Email": r.user_email, "Tier": r.tier, "Status": r.status,
                "Date": r.created_at, "Price": r.price, "Content": r.transcription,
                "Recipient": r.recipient_json, "Sender": r.sender_json, "Signature": r.signature_data
            })
        return data
    except: return []
    finally: db.close()

# --- ADDRESS BOOK ---
def add_contact(user_email, name, street, street2, city, state, zip_code, country="US"):
    db = get_session()
    if not db: return False
    try:
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
        db.commit()
        return True
    except Exception as e: return False
    finally: db.close()

def get_contacts(user_email):
    db = get_session()
    if not db: return []
    try: return db.query(SavedContact).filter(SavedContact.user_email == user_email).order_by(SavedContact.name).all()
    except: return []
    finally: db.close()

def delete_contact(contact_id):
    db = get_session()
    if not db: return False
    try:
        db.query(SavedContact).filter(SavedContact.id == contact_id).delete()
        db.commit()
        return True
    except: return False
    finally: db.close()

# --- RESTORED: GAMIFICATION ---
def get_civic_leaderboard():
    """Returns top 5 states by volume of Civic letters sent."""
    db = get_session()
    if not db: return []
    try:
        # Fetch all civic letters that are paid/sent
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
                    # Basic validation for US state codes
                    if state and len(state) == 2:
                        state_counts[state] = state_counts.get(state, 0) + 1
            except: continue
                
        # Sort by count desc
        sorted_stats = sorted(state_counts.items(), key=lambda item: item[1], reverse=True)
        return sorted_stats[:5]
    except Exception as e:
        print(f"Leaderboard Error: {e}")
        return []
    finally:
        db.close()