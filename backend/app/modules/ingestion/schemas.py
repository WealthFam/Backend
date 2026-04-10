from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import List, Optional, Any, Dict
from datetime import datetime
from decimal import Decimal

class IngestionBase(BaseModel):
    model_config = ConfigDict(strict=True, from_attributes=True)

class SmsPayload(IngestionBase):
    sender: str
    message: str
    device_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    received_at: Optional[datetime] = None

class EmailPayload(IngestionBase):
    subject: str
    body: str
    sender: str = "Manual Input"
    received_at: Optional[datetime] = None

class EmailSyncPayload(IngestionBase):
    imap_server: str = "imap.gmail.com"
    email: str
    password: str
    folder: str = "INBOX"
    unread_only: bool = True

class EmailConfigCreate(IngestionBase):
    email: str
    password: str
    imap_server: str = "imap.gmail.com"
    folder: str = "INBOX"
    auto_sync_enabled: bool = False
    user_id: Optional[str] = None

class EmailConfigRead(EmailConfigCreate):
    id: str
    is_active: bool
    last_sync_at: Optional[datetime] = None

class EmailConfigUpdate(IngestionBase):
    email: Optional[str] = None
    password: Optional[str] = None
    imap_server: Optional[str] = None
    folder: Optional[str] = None
    auto_sync_enabled: Optional[bool] = None
    user_id: Optional[str] = None
    reset_sync_history: bool = False
    last_sync_at: Optional[datetime] = None

class EmailSyncLogRead(IngestionBase):
    id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    items_processed: int = 0
    message: Optional[str] = None

class SpamFilterSchema(IngestionBase):
    id: str
    tenant_id: str
    sender: Optional[str] = None
    subject: Optional[str] = None
    source: Optional[str] = None
    count_blocked: int = 0
    created_at: datetime

    @field_validator('count_blocked', mode='before')
    @classmethod
    def convert_numeric_to_int(cls, v):
        if v is None:
            return 0
        return int(v)

class SpamFilterListResponse(IngestionBase):
    data: List[SpamFilterSchema]
    total: int

class TrainingMessageDismiss(IngestionBase):
    create_rule: bool = False

class TrainingBulkDismiss(IngestionBase):
    ids: List[str]
    create_rule: bool = False

class BulkDeleteEventsRequest(IngestionBase):
    event_ids: List[str]

class AliasCreate(IngestionBase):
    pattern: str
    alias: str
    update_past_transactions: bool = False

class AliasRead(IngestionBase):
    id: str
    pattern: str
    alias: str
    created_at: Optional[datetime] = None

class AliasPreviewRequest(IngestionBase):
    pattern: str

class IngestionEventRead(IngestionBase):
    id: str
    device_id: Optional[str] = None
    event_type: str
    status: str
    message: Optional[str] = None
    data_json: Optional[str] = None
    created_at: datetime

class TrainingLabelRequest(IngestionBase):
    amount: Decimal
    date: datetime
    account_mask: str
    recipient: Optional[str] = None
    category: Optional[str] = "Uncategorized"
    ref_id: Optional[str] = None
    balance: Optional[Decimal] = None
    credit_limit: Optional[Decimal] = None
    type: str = "DEBIT" # DEBIT or CREDIT
    generate_pattern: bool = True
    exclude_from_reports: bool = False

class PendingTransactionRead(IngestionBase):
    id: str
    account_id: str
    account_name: Optional[str] = None
    account_owner_name: Optional[str] = None
    amount: Decimal
    date: datetime
    description: Optional[str] = None
    recipient: Optional[str] = None
    category: Optional[str] = None
    source: str
    is_transfer: bool = False
    to_account_id: Optional[str] = None
    exclude_from_reports: bool = False
    created_at: datetime
    external_id: Optional[str] = None

class TriageListResponse(IngestionBase):
    data: List[PendingTransactionRead]
    total: int
    limit: int
    skip: int
