import streamlit as st
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
import json
import secrets_manager

Base = declarative_base()

# --- THE AUDIT TABLE ---
class AuditEvent(Base):
    __tablename__ = "audit_events"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_email = Column(String, index=True)
    stripe_session_id = Column(String, index=True, nullable=True) # The "Golden Thread"
    event_type = Column(String) # e.g., "PAYMENT_SUCCESS", "MAIL_FAILED"
    details = Column(Text) # JSON blob of errors or context

# --- SETUP ---
@st.cache_resource
def get_engine():
    db_url = secrets_manager.get_secret("DATABASE_URL")
    if db_url:
        db_url = db_url.replace("postgres://", "postgresql://")
    else:
        db_url = "sqlite:///local_audit.db"
    
    try:
        engine = create_engine(db_url, pool_pre_ping=True)
        Base.metadata.create_all(bind=engine)
        return engine
    except: return None

def get_session():
    engine = get_engine()
    if not engine: return None
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()

# --- CORE LOGGING FUNCTION ---
def log_event(user_email, event_type, session_id=None, data=None):
    """
    Call this anywhere in the app to record an action.
    """
    db = get_session()
    if not db: return
    
    try:
        # Convert dict data to JSON string for storage
        details_str = json.dumps(data) if data else "{}"
        
        event = AuditEvent(
            user_email=user_email,
            stripe_session_id=session_id,
            event_type=event_type,
            details=details_str
        )
        db.add(event)
        db.commit()
        print(f"📝 Audit Log: {event_type} for {user_email}")
    except Exception as e:
        print(f"❌ Audit Fail: {e}")
    finally:
        db.close()

# --- ADMIN LOOKUP ---
def get_trace(session_id):
    """Returns the full timeline for a specific payment ID"""
    db = get_session()
    if not db: return []
    try:
        return db.query(AuditEvent).filter(AuditEvent.stripe_session_id == session_id).order_by(AuditEvent.timestamp).all()
    finally: db.close()

def get_recent_failures(limit=20):
    """Finds recent errors to help you spot bugs"""
    db = get_session()
    if not db: return []
    try:
        # Look for events containing "FAIL" or "ERROR"
        return db.query(AuditEvent).filter(AuditEvent.event_type.contains("FAIL")).order_by(AuditEvent.timestamp.desc()).limit(limit).all()
    finally: db.close()
