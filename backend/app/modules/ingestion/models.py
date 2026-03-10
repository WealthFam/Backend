import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Numeric
from sqlalchemy.orm import relationship
from backend.app.core.database import Base
from backend.app.core import timezone
from backend.app.core.timezone import UTCDateTime

class EmailConfiguration(Base):
    __tablename__ = "email_configurations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)  # Link to family member
    email = Column(String, nullable=False)
    # Note: In a real app, encrypt this. For now, storing as-is.
    password = Column(String, nullable=False) 
    imap_server = Column(String, default="imap.gmail.com", nullable=False)
    folder = Column(String, default="INBOX", nullable=False)
    is_active = Column(Boolean, default=True)
    auto_sync_enabled = Column(Boolean, default=False)
    last_sync_at = Column(UTCDateTime, nullable=True) # General expense sync
    cas_last_sync_at = Column(UTCDateTime, nullable=True) # Mutual fund CAS sync
    created_at = Column(UTCDateTime, default=timezone.utcnow)

class EmailSyncLog(Base):
    __tablename__ = "email_sync_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    config_id = Column(String, ForeignKey("email_configurations.id"), nullable=False, index=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    started_at = Column(UTCDateTime, default=timezone.utcnow)
    completed_at = Column(UTCDateTime, nullable=True)
    status = Column(String, default="running") # running, completed, error
    items_processed = Column(Numeric(10, 0), default=0)
    message = Column(String, nullable=True) # JSON or text log

class PendingTransaction(Base):
    __tablename__ = "pending_transactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    account_id = Column(String, nullable=False, index=True)  # No FK for DuckDB compliance
    
    # Relationships
    account = relationship("Account", 
                          primaryjoin="PendingTransaction.account_id == foreign(remote(Account.id))",
                          viewonly=True,
                          uselist=False,
                          sync_backref=False)
    amount = Column(Numeric(15, 2), nullable=False)
    date = Column(UTCDateTime, nullable=False)
    description = Column(String, nullable=True)
    recipient = Column(String, nullable=True)
    category = Column(String, nullable=True)
    source = Column(String, nullable=False) # SMS, EMAIL
    raw_message = Column(String, nullable=True)
    content_hash = Column(String, nullable=True, index=True)
    external_id = Column(String, nullable=True) # Reference Number/UTR
    is_transfer = Column(Boolean, default=False, nullable=False)
    to_account_id = Column(String, nullable=True) # Destination Account ID for transfers
    balance_is_synced = Column(Boolean, default=False, nullable=False) # True if account balance was updated at ingestion
    latitude = Column(Numeric(10, 8), nullable=True)
    longitude = Column(Numeric(11, 8), nullable=True)
    location_name = Column(String, nullable=True)
    expense_group_id = Column(String, nullable=True) # No FK to keep ingestion decoupled
    exclude_from_reports = Column(Boolean, default=False, nullable=False)
    created_at = Column(UTCDateTime, default=timezone.utcnow)

class MobileDevice(Base):
    __tablename__ = "mobile_devices"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True) # Optional link to specific user

    device_name = Column(String, nullable=False)
    device_id = Column(String, nullable=False, unique=True)
    fcm_token = Column(String, nullable=True)
    is_approved = Column(Boolean, default=False)
    is_enabled = Column(Boolean, default=True)  # Toggle for ingestion
    is_ignored = Column(Boolean, default=False) # Soft Reject
    last_seen_at = Column(UTCDateTime, default=timezone.utcnow)
    created_at = Column(UTCDateTime, default=timezone.utcnow)

class UnparsedMessage(Base):
    __tablename__ = "unparsed_messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    source = Column(String, nullable=False) # SMS, EMAIL
    raw_content = Column(String, nullable=False)
    content_hash = Column(String, nullable=True, index=True)
    subject = Column(String, nullable=True)
    sender = Column(String, nullable=True)
    created_at = Column(UTCDateTime, default=timezone.utcnow)

class ParsingPattern(Base):
    __tablename__ = "parsing_patterns"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    pattern_type = Column(String, default="regex") # regex, template
    pattern_value = Column(String, nullable=False) # The regex or template string
    mapping_config = Column(String, nullable=False) # JSON: { "amount": 1, "date": 2, ... }
    is_active = Column(Boolean, default=True)
    description = Column(String, nullable=True)
    created_at = Column(UTCDateTime, default=timezone.utcnow)

class AIConfiguration(Base):
    __tablename__ = "ai_configurations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    provider = Column(String, default="gemini") # gemini, openai, etc.
    model_name = Column(String, default="gemini-pro")
    api_key = Column(String, nullable=True) # Sensitive
    is_enabled = Column(Boolean, default=True)
    
    # Store prompts as a JSON string to keep it agnostic and extensible
    # { "parsing": "...", "insights": "..." }
    prompts_json = Column(String, nullable=True) 
    
    created_at = Column(UTCDateTime, default=timezone.utcnow)
    updated_at = Column(UTCDateTime, default=timezone.utcnow, onupdate=timezone.utcnow)

class AICallCache(Base):
    __tablename__ = "ai_call_cache"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    content_hash = Column(String, index=True, nullable=False)
    provider = Column(String, nullable=False)
    model_name = Column(String, nullable=False)
    response_json = Column(String, nullable=False)
    created_at = Column(UTCDateTime, default=timezone.utcnow)

class IngestionEvent(Base):
    __tablename__ = "ingestion_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    device_id = Column(String, nullable=True, index=True) # Optional link to MobileDevice.device_id
    event_type = Column(String, nullable=False) # sms_received, heartbeat, email_received, parse_failed, etc.
    status = Column(String, nullable=False) # success, error, warning, skipped
    message = Column(String, nullable=True)
    data_json = Column(String, nullable=True) # Extra metadata like sender, message preview, etc.
    created_at = Column(UTCDateTime, default=timezone.utcnow)

class IgnoredPattern(Base):
    __tablename__ = "ignored_patterns"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    pattern = Column(String, nullable=False) # merchant, description or recipient
    source = Column(String, nullable=True) # SMS, EMAIL, ALL
    created_at = Column(UTCDateTime, default=timezone.utcnow)

class AIInsightCache(Base):
    __tablename__ = "ai_insight_cache"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    insight_type = Column(String, nullable=False, index=True) # e.g. "dashboard_summary", "loan_advice"
    content = Column(String, nullable=False) # Storing the JSON response as string
    created_at = Column(UTCDateTime, default=timezone.utcnow)
    updated_at = Column(UTCDateTime, default=timezone.utcnow, onupdate=timezone.utcnow)
