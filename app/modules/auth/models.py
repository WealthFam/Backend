import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SqlEnum, Boolean
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.core.timezone import UTCDateTime
from backend.app.core import timezone
import enum

class UserRole(str, enum.Enum):
    OWNER = "OWNER"
    ADULT = "ADULT"
    CHILD = "CHILD"
    GUEST = "GUEST"

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    created_at = Column(UTCDateTime, default=timezone.utcnow)

    users = relationship("User", back_populates="tenant")

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    avatar = Column(String, nullable=True) # Emoji or color or URL
    dob = Column(UTCDateTime, nullable=True)
    pan_number = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    role = Column(SqlEnum(UserRole), default=UserRole.ADULT, nullable=False)
    # Storing scopes as minimal JSON string or use a separate table if needed.
    # For DuckDB/SQLite, simple JSON string is often easiest if no native JSON type.
    scopes = Column(String, nullable=True) 

    tenant = relationship("Tenant", back_populates="users")

class TenantSetting(Base):
    __tablename__ = "tenant_settings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    key = Column(String, nullable=False, index=True) # e.g. "parser_service_url"
    value = Column(String, nullable=True) # e.g. "http://localhost:8001/v1"
    updated_at = Column(UTCDateTime, default=timezone.utcnow, onupdate=timezone.utcnow)

class UserToken(Base):
    """Tracks active/revoked sessions using JWT JTIs"""
    __tablename__ = "user_tokens"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    token_jti = Column(String, unique=True, index=True, nullable=False)
    expires_at = Column(UTCDateTime, nullable=False)
    is_revoked = Column(Boolean, default=False)
    created_at = Column(UTCDateTime, default=timezone.utcnow)

