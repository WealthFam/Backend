import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Boolean
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import relationship, backref
import enum
from backend.app.core.database import Base

class DocumentType(str, enum.Enum):
    INVOICE = "INVOICE"
    POLICY = "POLICY"
    TAX = "TAX"
    IDENTITY = "IDENTITY"
    OTHER = "OTHER"

class DocumentVault(Base):
    __tablename__ = "document_vault"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    owner_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    
    filename = Column(String, nullable=False) # Folder name or file name
    file_type = Column(SqlEnum(DocumentType), default=DocumentType.OTHER, nullable=False)
    file_path = Column(String, nullable=True) # Current version path (Null for folders)
    file_size = Column(Numeric(15, 0), default=0, nullable=False) # Size in bytes
    mime_type = Column(String, nullable=True)
    thumbnail_path = Column(String, nullable=True)
    
    transaction_id = Column(String, nullable=True, index=True)  # No FK — DuckDB FKs block UPDATE on parent rows
    parent_id = Column(String, nullable=True, index=True) # Manual FK for DuckDB compatibility
    is_folder = Column(Boolean, default=False, nullable=False)
    is_shared = Column(Boolean, default=True, nullable=False) # Default to family shared
    description = Column(String, nullable=True)
    
    # Cloud Sync & Versioning
    gdrive_file_id = Column(String, nullable=True, index=True)
    last_synced_at = Column(DateTime, nullable=True)
    current_version = Column(Numeric(5, 0), default=1)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships are handled here or via backrefs from other modules
    # In FastAPI/SQLAlchemy, its often easier to import from finance if needed
    # but for true isolation we rely on string-based ForeignKey and backrefs.
    
    owner = relationship("User", foreign_keys=[owner_id])
    children = relationship(
        "DocumentVault", 
        primaryjoin="DocumentVault.id == foreign(DocumentVault.parent_id)",
        backref=backref("parent", remote_side=[id])
    )
    versions = relationship(
        "DocumentVersion", 
        primaryjoin="DocumentVault.id == foreign(DocumentVersion.document_id)",
        back_populates="document", 
        cascade="all, delete-orphan"
    )

    # Added relationship to Transaction (without strict FK)
    transaction = relationship(
        "Transaction",
        primaryjoin="DocumentVault.transaction_id == foreign(Transaction.id)",
        uselist=False,
        viewonly=True
    )

class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, nullable=False, index=True) # Manual FK for DuckDB compatibility
    version_number = Column(Numeric(5, 0), nullable=False)
    
    file_path = Column(String, nullable=False)
    file_size = Column(Numeric(15, 0), nullable=False)
    filename = Column(String, nullable=False)
    thumbnail_path = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    document = relationship(
        "DocumentVault", 
        primaryjoin="DocumentVault.id == foreign(DocumentVersion.document_id)",
        back_populates="versions"
    )

class VaultSyncHistory(Base):
    __tablename__ = "vault_sync_history"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    status = Column(String, nullable=False) # success, error, running
    message = Column(String, nullable=True)
    items_processed = Column(Numeric(10, 0), default=0)
    error_details = Column(String, nullable=True)
    
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

