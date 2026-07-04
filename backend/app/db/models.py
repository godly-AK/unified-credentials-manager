from sqlalchemy import Column, String, Boolean, TIMESTAMP, func
from app.db.database import Base

class User(Base):
    __tablename__ = "users"

    username = Column(String, primary_key=True)
    password_hash = Column(String, nullable=False)
    emails = Column(String, nullable=True) # For web registration
    last_access_time = Column(TIMESTAMP(timezone=True), default=func.now())
    token = Column(String, nullable=True) # Encrypted session token for web
    last_ip_addr = Column(String, nullable=True)
    public_key = Column(String, nullable=True) # For mobile challenge reset
    fcm_token = Column(String, nullable=True) # For push notifications
    passwd_changed = Column(TIMESTAMP(timezone=True), default=func.now())
    blocked = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True), default=func.now())

class ResetChallenge(Base):
    __tablename__ = "reset_challenges"
    
    username = Column(String, primary_key=True)
    challenge_b64 = Column(String)
    created_at = Column(TIMESTAMP(timezone=True), default=func.now())
