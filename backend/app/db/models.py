from sqlalchemy import Boolean, Column, ForeignKey, Integer, JSON, String, TIMESTAMP, false, func
from sqlalchemy.orm import relationship

from app.db.database import Base

class User(Base):
    __tablename__ = "users"

    username = Column(String, primary_key=True)
    password_hash = Column(String, nullable=False)
    email = Column("emails", String, nullable=False, unique=True, index=True)
    last_access_time = Column(TIMESTAMP(timezone=True), default=func.now())
    last_ip_addr = Column(String, nullable=True)
    public_key = Column(String, nullable=True)
    passwd_changed = Column(TIMESTAMP(timezone=True), default=func.now())
    blocked = Column(Boolean, default=False)
    is_admin = Column(Boolean, nullable=False, default=False, server_default=false())
    created_at = Column(TIMESTAMP(timezone=True), default=func.now())

    password_history = relationship(
        "PasswordHistory",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class PasswordHistory(Base):
    __tablename__ = "password_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, ForeignKey("users.username", ondelete="CASCADE"), nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), default=func.now(), nullable=False)

    user = relationship("User", back_populates="password_history")


class SecurityEvent(Base):
    __tablename__ = "security_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String, nullable=False, index=True)
    username = Column(String, nullable=True, index=True)
    ip_address = Column(String, nullable=True)
    risk_level = Column(String, nullable=False, default="LOW")
    details = Column(JSON, nullable=False, default=dict)
    created_at = Column(TIMESTAMP(timezone=True), default=func.now(), nullable=False, index=True)


class SecurityAlertReview(Base):
    __tablename__ = "security_alert_reviews"

    event_id = Column(Integer, ForeignKey("security_events.id", ondelete="CASCADE"), primary_key=True)
    reviewed_by = Column(String, nullable=False)
    note = Column(String(500), nullable=False)
    reviewed_at = Column(TIMESTAMP(timezone=True), nullable=False)


class AuditExportCheckpoint(Base):
    __tablename__ = "audit_export_checkpoints"

    destination = Column(String, primary_key=True)
    last_event_id = Column(Integer, nullable=False, default=0)

class ResetChallenge(Base):
    __tablename__ = "reset_challenges"
    
    username = Column(String, primary_key=True)
    challenge_b64 = Column(String)
    created_at = Column(TIMESTAMP(timezone=True), default=func.now())


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    id = Column(String, primary_key=True)
    username = Column(String, ForeignKey("users.username", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String, nullable=False, unique=True, index=True)
    _csrf_ciphertext = Column("csrf_token", String, nullable=False)
    client_type = Column(String, nullable=False, default="web")
    ip_address = Column(String, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    last_seen_at = Column(TIMESTAMP(timezone=True), nullable=False)
    revoked_at = Column(TIMESTAMP(timezone=True), nullable=True)

    @property
    def csrf_token(self):
        from app.core.encryption import decrypt_secret
        return decrypt_secret(self._csrf_ciphertext, f"ucm/session/{self.id}/{self.username}")

    @csrf_token.setter
    def csrf_token(self, value):
        from app.core.encryption import encrypt_secret
        self._csrf_ciphertext = encrypt_secret(value, f"ucm/session/{self.id}/{self.username}")


class WorkplaceNode(Base):
    __tablename__ = "workplace_nodes"
    id = Column(String, primary_key=True)
    username = Column(String, ForeignKey("users.username", ondelete="CASCADE"), nullable=False, index=True)
    slot = Column(String, nullable=False)
    label = Column(String, nullable=False)
    public_key = Column(String, nullable=False)
    revoked_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False)


class NodeEnrollmentTicket(Base):
    __tablename__ = "node_enrollment_tickets"
    token_hash = Column(String, primary_key=True)
    username = Column(String, ForeignKey("users.username", ondelete="CASCADE"), nullable=False, index=True)
    slot = Column(String, nullable=False)
    label = Column(String, nullable=False)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)


class LoginTrustChallenge(Base):
    __tablename__ = "login_trust_challenges"
    id = Column(String, primary_key=True)
    username = Column(String, ForeignKey("users.username", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String, ForeignKey("auth_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    nonce = Column(String, nullable=False)
    approval_code = Column(String(8), unique=True, index=True, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    phone_approved_at = Column(TIMESTAMP(timezone=True), nullable=True)
    node_a_approved_at = Column(TIMESTAMP(timezone=True), nullable=True)
    node_b_approved_at = Column(TIMESTAMP(timezone=True), nullable=True)


class SessionTrust(Base):
    __tablename__ = "session_trust"
    session_id = Column(String, ForeignKey("auth_sessions.id", ondelete="CASCADE"), primary_key=True)
    level = Column(String, nullable=False)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
