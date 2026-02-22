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
    
    transaction_id = Column(String, ForeignKey("transactions.id"), nullable=True, index=True)
    parent_id = Column(String, ForeignKey("document_vault.id"), nullable=True, index=True)
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
    children = relationship("DocumentVault", backref=backref("parent", remote_side=[id]), cascade="all, delete-orphan")
    versions = relationship("DocumentVersion", back_populates="document", cascade="all, delete-orphan")

class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("document_vault.id"), nullable=False, index=True)
    version_number = Column(Numeric(5, 0), nullable=False)
    
    file_path = Column(String, nullable=False)
    file_size = Column(Numeric(15, 0), nullable=False)
    filename = Column(String, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    document = relationship("DocumentVault", back_populates="versions")
