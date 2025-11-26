import streamlit as st
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
from typing import Any, Tuple, Dict
import json

# --- GLOBAL SETUP ---
Base = declarative_base()

class UserProfile(Base):
    __tablename__ = "user_profiles"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    address_line1 = Column(String)
    address_city = Column(String)
    address_state = Column(String)
    address_zip = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class LetterDraft(Base):
    __tablename__ = "letter_drafts"
    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, index=True)
    transcription = Column(Text)  # The body text
    status = Column(String, default="Draft") 
    tier = Column(String)
    price = Column(String)
    
    # --- NEW COLUMNS ---
    recipient_json = Column(Text) # Stores JSON string of to_addr
    sender_json = Column(Text)    # Stores JSON string of from_addr
    signature_data = Column(Text) # Stores Base64 or raw signature data
    
    created_at = Column(DateTime, default=datetime.utcnow)

# --- ENGINE ---
@st.cache_resource
def get_engine():
    if "DATABASE_URL" in st.secrets:
        db_url = st.secrets["DATABASE_URL"].replace("postgres://", "postgresql://")
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

# --- FUNCTIONS ---

def get_user_profile(email):
    db = get_session()
    if not db: return None
    try: return db.query(UserProfile).filter(UserProfile.email == email).first()
    except: return None
    finally: db.close()

# UPDATED SAVE FUNCTION
def save_draft(email, text, tier, price, to_addr=None, from_addr=None, sig_data=None, status="Draft"):
    db = get_session()
    if not db: return None
    try:
        # Convert dicts to JSON strings for storage
        r_json = json.dumps(to_addr) if to_addr else "{}"
        s_json = json.dumps(from_addr) if from_addr else "{}"
        
        draft = LetterDraft(
            user_email=email, 
            transcription=text, 
            tier=tier, 
            price=str(price), 
            status=status,
            recipient_json=r_json,
            sender_json=s_json,
            signature_data=str(sig_data) if sig_data is not None else None
        )
        db.add(draft); db.commit(); db.refresh(draft)
        return draft.id
    except Exception as e:
        print(f"Save Error: {e}")
        db.rollback(); return None
    finally: db.close()

def update_user_profile(email, name, street, city, state, zip_code):
    db = get_session()
    if not db: return
    try:
        user = db.query(UserProfile).filter(UserProfile.email == email).first()
        if not user:
            user = UserProfile(email=email); db.add(user)
        user.full_name = name; user.address_line1 = street; user.address_city = city
        user.address_state = state; user.address_zip = zip_code
        db.commit()
    except: pass
    finally: db.close()

def fetch_all_drafts():
    """Returns drafts including the new JSON fields."""
    db = get_session()
    if not db: return []
    try:
        results = db.query(LetterDraft).order_by(LetterDraft.created_at.desc()).all()
        data = []
        for r in results:
            data.append({
                "ID": r.id,
                "Email": r.user_email,
                "Tier": r.tier,
                "Status": r.status,
                "Date": r.created_at,
                "Price": r.price,
                "Content": r.transcription,
                "Recipient": r.recipient_json, # NEW
                "Sender": r.sender_json,       # NEW
                "Signature": r.signature_data  # NEW
            })
        return data
    except: return []
    finally: db.close()