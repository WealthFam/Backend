import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
from backend.app.core.database import Base
from backend.app.core.timezone import UTCDateTime
from backend.app.core import timezone

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True) # Receiver (None = All Family)
    
    title = Column(String, nullable=False)
    body = Column(String, nullable=False)
    category = Column(String, default="INFO") # INFO, EXPENSE, EMERGENCY
    
    is_read = Column(Boolean, default=False)
    created_at = Column(UTCDateTime, default=timezone.utcnow)
    expires_at = Column(UTCDateTime, nullable=True) # For auto-cleanup
