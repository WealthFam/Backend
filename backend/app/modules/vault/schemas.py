from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from decimal import Decimal
from .models import DocumentType
from backend.app.modules.finance.schemas import TransactionRead

class SimpleTransaction(BaseModel):
    id: str
    description: str
    amount: Decimal
    date: datetime
    category: Optional[str] = None

class DocumentBase(BaseModel):
    filename: str
    file_type: DocumentType = DocumentType.OTHER
    description: Optional[str] = None
    is_shared: bool = True
    transaction_id: Optional[str] = None
    parent_id: Optional[str] = None

class DocumentCreate(DocumentBase):
    pass

class DocumentRead(DocumentBase):
    id: str
    tenant_id: str
    owner_id: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Decimal = Decimal('0')
    mime_type: Optional[str] = None
    is_folder: bool = False
    current_version: int = 1
    created_at: datetime
    updated_at: datetime
    linked_transaction: Optional[SimpleTransaction] = None

    class Config:
        from_attributes = True

class DocumentVersionRead(BaseModel):
    id: str
    document_id: str
    version_number: int
    file_path: str
    file_size: Decimal
    filename: str
    created_at: datetime

    class Config:
        from_attributes = True

class FolderCreate(BaseModel):
    name: str
    parent_id: Optional[str] = None
    is_shared: bool = True
    description: Optional[str] = None
