from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict

from .models import DocumentType


class SimpleTransaction(BaseModel):
    model_config = ConfigDict(strict=True, from_attributes=True)
    
    id: str
    description: str
    amount: Decimal
    date: datetime
    category: Optional[str] = None
    account_name: Optional[str] = None


class DocumentBase(BaseModel):
    model_config = ConfigDict(strict=True, from_attributes=True)
    
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
    transaction: Optional[SimpleTransaction] = None


class DocumentVersionRead(BaseModel):
    model_config = ConfigDict(strict=True, from_attributes=True)
    
    id: str
    document_id: str
    version_number: int
    file_path: str
    file_size: Decimal
    filename: str
    created_at: datetime


class FolderCreate(BaseModel):
    model_config = ConfigDict(strict=True, from_attributes=True)
    
    name: str
    parent_id: Optional[str] = None
    is_shared: bool = True
    description: Optional[str] = None
