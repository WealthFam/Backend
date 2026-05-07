from pydantic import BaseModel, ConfigDict, Field, field_validator, BeforeValidator
from typing import List, Optional, Any, Dict, Annotated
from datetime import datetime
from decimal import Decimal

# --- Ingestion Coercion Utilities ---
# Ensures high-precision timestamps from mobile devices are parsed 
# correctly even when strict validation is enabled.

def coerce_datetime(v: Any) -> Any:
    """Proactively convert ISO strings from mobile payloads into datetime objects."""
    if v is None: return None
    if isinstance(v, str):
        # Clean the string for common ISO variations
        cleaned = v.replace("Z", "+00:00").replace(" ", "T")
        try:
            # Try native first
            return datetime.fromisoformat(cleaned)
        except:
            try:
                # Handle cases with too many sub-seconds or other oddities
                # Often occurs on Android/Flutter JSON encoding
                if "." in cleaned:
                    base, rest = cleaned.split(".", 1)
                    # Keep only first 6 digits of sub-seconds for Python's %f (microseconds)
                    sub = ""
                    tz = ""
                    for i, char in enumerate(rest):
                        if char.isdigit():
                            if i < 6: sub += char
                        else:
                            tz = rest[i:]
                            break
                    # Reconstruct: YYYY-MM-DDTHH:MM:SS.ffffff+HH:MM
                    return datetime.fromisoformat(f"{base}.{sub.ljust(6, '0')}{tz}")
            except:
                pass
            return v
    return v

class IngestionBase(BaseModel):
    model_config = ConfigDict(strict=False, from_attributes=True)

class SmsPayload(IngestionBase):
    sender: str
    message: str
    device_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    date: Optional[str] = None
    received_at: Optional[Annotated[datetime, BeforeValidator(coerce_datetime)]] = None

class EmailPayload(IngestionBase):
    subject: str
    body: str
    sender: str = "Manual Input"
    received_at: Optional[Annotated[datetime, BeforeValidator(coerce_datetime)]] = None

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

class EmailSyncItemLogRead(IngestionBase):
    id: str
    subject: Optional[str] = None
    sender: Optional[str] = None
    received_at: Optional[datetime] = None
    status: str
    reason: Optional[str] = None
    parser_used: Optional[str] = None
    transaction_id: Optional[str] = None
    created_at: datetime

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
    account_mask: Optional[str] = None
    account_id: Optional[str] = None
    recipient: Optional[str] = None
    category: Optional[str] = "Uncategorized"
    ref_id: Optional[str] = None
    balance: Optional[Decimal] = None
    credit_limit: Optional[Decimal] = None
    type: str = "DEBIT" # DEBIT or CREDIT
    generate_pattern: bool = True
    apply_to_unparsed: bool = True
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
