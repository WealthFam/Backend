from typing import List, Dict, Optional, Any
from datetime import datetime
import json
from fastapi import APIRouter, Depends, HTTPException, Body, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session
from backend.app.core.database import get_db

from backend.app.modules.auth import models as auth_models
from backend.app.modules.auth.dependencies import get_current_user

from backend.app.modules.finance import schemas as finance_schemas
from backend.app.modules.finance import models as finance_models
from backend.app.modules.finance.services.transaction_service import TransactionService

from backend.app.modules.ingestion.services import IngestionService
from backend.app.modules.ingestion import models as ingestion_models
from backend.app.modules.ingestion.pattern_service import PatternGenerator
from backend.app.modules.ingestion.email_sync import EmailSyncService
# Legacy parsers removed in favor of ExternalParserService

router = APIRouter(tags=["Ingestion"])


class SmsPayload(BaseModel):
    sender: str
    message: str
    device_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    received_at: Optional[datetime] = None

class EmailPayload(BaseModel):
    subject: str
    body: str
    sender: Optional[str] = "Manual Input"
    received_at: Optional[datetime] = None

class EmailSyncPayload(BaseModel):
    imap_server: str = "imap.gmail.com"
    email: str
    password: str # App Password recommended
    folder: str = "INBOX"
    unread_only: bool = True

class EmailConfigCreate(BaseModel):
    email: str
    password: str
    imap_server: str = "imap.gmail.com"
    folder: str = "INBOX"
    auto_sync_enabled: bool = False
    user_id: Optional[str] = None

class EmailConfigUpdate(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None
    imap_server: Optional[str] = None
    folder: Optional[str] = None
    auto_sync_enabled: Optional[bool] = None
    user_id: Optional[str] = None
    reset_sync_history: Optional[bool] = False
    last_sync_at: Optional[datetime] = None

class EmailSyncLogRead(BaseModel):
    id: str
    started_at: datetime
    completed_at: Optional[datetime]
    status: str
    items_processed: float
    message: Optional[str]
    
    class Config:
        from_attributes = True

class EmailConfigRead(EmailConfigCreate):
    id: str
    is_active: bool
    auto_sync_enabled: bool = False
    last_sync_at: Optional[datetime] = None

@router.post("/sms")
def ingest_sms(
    payload: SmsPayload,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ingest a raw SMS message, parse it, and SAVE the transaction if account matches.
    """
    # 1. Device Authorization Check
    if payload.device_id:
        device = db.query(ingestion_models.MobileDevice).filter(
            ingestion_models.MobileDevice.device_id == payload.device_id,
            ingestion_models.MobileDevice.tenant_id == str(current_user.tenant_id)
        ).first()

        if not device:
             # Unknown device, reject or log?
             IngestionService.log_event(
                 db, 
                 str(current_user.tenant_id), 
                 "sms_received", 
                 "error", 
                 f"Device not registered: {payload.device_id}",
                 device_id=payload.device_id
             )
             raise HTTPException(status_code=403, detail="Device not registered or found")

        if not device.is_approved:
            IngestionService.log_event(
                db, 
                str(current_user.tenant_id), 
                "sms_received", 
                "warning", 
                "Device not approved by owner",
                device_id=payload.device_id
            )
            raise HTTPException(status_code=403, detail="Device not approved by owner")
            
        if not device.is_enabled:
            return {"status": "skipped", "reason": "Ingestion disabled for this device"}
            
        # Update last seen
        device.last_seen_at = datetime.utcnow()
        db.commit()

    # 2. Parsing (Call External Microservice)
    from backend.app.modules.ingestion.parser_service import ExternalParserService
    from backend.app.modules.ingestion.base import ParsedTransaction

    parser_response = ExternalParserService.parse_sms(payload.sender, payload.message, received_at=payload.received_at)
    
    # Accept "processed", "success", and "duplicate_submission"
    status = parser_response.get("status") if parser_response else "offline"
    
    if status == "ignored":
        return {"status": "skipped", "message": "Ignored by parser (Non-financial)"}

    if not parser_response or status not in ["processed", "success", "duplicate_submission"]:
        # Capture as unparsed for training
        IngestionService.capture_unparsed(db, str(current_user.tenant_id), "SMS", payload.message, sender=payload.sender)
        
        IngestionService.log_event(
            db, str(current_user.tenant_id), "sms_ingestion", "warning",
            f"External parser skipped/failed with status: {status}",
            data={
                "sender": payload.sender, 
                "message": payload.message, 
                "parser_status": status,
                "parser_logs": parser_response.get("logs") if parser_response else []
            },
            device_id=payload.device_id
        )
        return {"status": "unparsed", "message": f"Message not identified as transaction (Status: {status})"}

    if status == "duplicate_submission":
        return {"status": "skipped", "message": "Duplicate submission detected by parser service."}

    # 3. Process Multiple Results (if any)
    results = []
    # The external parser returns IngestionResult: { status: str, results: List[ParsedItem] }
    for item in parser_response.get("results", []):
        t = item.get("transaction")
        if not t: continue
        
        # Robust Date Parsing
        txn_date = t.get("date")
        if isinstance(txn_date, str):
            try:
                txn_date = datetime.fromisoformat(txn_date.replace("Z", "+00:00"))
            except:
                txn_date = datetime.utcnow()
        else:
            txn_date = datetime.utcnow()

        # Map to ParsedTransaction
        parsed = ParsedTransaction(
            amount=t.get("amount"),
            date=txn_date,
            description=t.get("description") or t.get("raw_message") or payload.message,
            type=t.get("type", "DEBIT").upper(),
            account_mask=t.get("account", {}).get("mask"),
            recipient=t.get("recipient") or t.get("merchant", {}).get("cleaned"),
            category=t.get("category"),
            ref_id=t.get("ref_id"),
            balance=t.get("balance"),
            credit_limit=t.get("credit_limit"),
            raw_message=t.get("raw_message") or payload.message,
            source="SMS",
            is_ai_parsed=str(item.get("metadata", {}).get("parser_used", "")).upper() == "AI"
        )
        
        extra_data = {
            "latitude": payload.latitude,
            "longitude": payload.longitude,
            "device_id": payload.device_id
        }
            
        proc_result = IngestionService.process_transaction(db, str(current_user.tenant_id), parsed, extra_data=extra_data)
        results.append(proc_result)

    IngestionService.log_event(
        db, 
        str(current_user.tenant_id), 
        "sms_ingestion", 
        "success", 
        f"Processed SMS from {payload.sender} via External Parser", 
        data={"sender": payload.sender, "results_count": len(results), "details": results},
        device_id=payload.device_id
    )
    
    return {
        "status": "processed",
        "results": results
    }

@router.post("/email")
def ingest_email(
    payload: EmailPayload,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ingest a raw Email, parse it, and SAVE the transaction if account matches.
    """
    # 2. Parsing (Call External Microservice)
    from backend.app.modules.ingestion.parser_service import ExternalParserService
    from backend.app.modules.ingestion.base import ParsedTransaction

    parser_response = ExternalParserService.parse_email(payload.subject, payload.body, payload.sender or "Manual Input", received_at=payload.received_at)
    
    status = parser_response.get("status") if parser_response else "offline"
    
    if status == "ignored":
        return {"status": "skipped", "message": "Ignored by parser (Non-financial)"}

    if not parser_response or status not in ["processed", "success", "duplicate_submission"]:
        IngestionService.log_event(
            db, str(current_user.tenant_id), "email_ingestion", "error",
            f"External parser skipped/failed with status: {status}",
            data={"subject": payload.subject, "parser_status": status}
        )
        raise HTTPException(status_code=422, detail=f"External parser failed for Email content (Status: {status})")

    if status == "duplicate_submission":
        return {"status": "skipped", "message": "Duplicate submission detected by parser service."}
        
    # 3. Process Multiple Results
    results = []
    for item in parser_response.get("results", []):
        t = item.get("transaction")
        if not t: continue
        
        # Robust Date Parsing
        txn_date = t.get("date")
        if isinstance(txn_date, str):
            try:
                txn_date = datetime.fromisoformat(txn_date.replace("Z", "+00:00"))
            except:
                txn_date = datetime.utcnow()
        else:
            txn_date = datetime.utcnow()

        # Map to ParsedTransaction
        parsed = ParsedTransaction(
            amount=t.get("amount"),
            date=txn_date,
            description=t.get("description") or payload.subject,
            type=t.get("type", "DEBIT").upper(),
            account_mask=t.get("account", {}).get("mask"),
            recipient=t.get("recipient") or t.get("merchant", {}).get("cleaned"),
            category=t.get("category"),
            ref_id=t.get("ref_id"),
            balance=t.get("balance"),
            credit_limit=t.get("credit_limit"),
            raw_message=t.get("raw_message") or payload.body,
            source="EMAIL",
            is_ai_parsed=str(item.get("metadata", {}).get("parser_used", "")).upper() == "AI"
        )
        
        proc_result = IngestionService.process_transaction(db, str(current_user.tenant_id), parsed)
        results.append(proc_result)
    
    return {
        "status": "processed",
        "results": results
    }

@router.post("/email/sync")
def sync_email_inbox(
    payload: EmailSyncPayload,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Connect to IMAP and scan for transactions.
    """
    search_crit = 'UNSEEN' if payload.unread_only else 'ALL'
    
    result = EmailSyncService.sync_emails(
        db=db,
        tenant_id=str(current_user.tenant_id),
        imap_server=payload.imap_server,
        email_user=payload.email,
        email_pass=payload.password,
        folder=payload.folder,
        search_criterion=search_crit
    )
    
    return result

@router.get("/email/configs", response_model=List[EmailConfigRead])
def list_email_configs(
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(ingestion_models.EmailConfiguration).filter(
        ingestion_models.EmailConfiguration.tenant_id == str(current_user.tenant_id)
    ).all()

@router.post("/email/configs", response_model=EmailConfigRead)
def create_email_config(
    payload: EmailConfigCreate,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    config = ingestion_models.EmailConfiguration(
        tenant_id=str(current_user.tenant_id),
        **payload.dict()
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return config

@router.put("/email/configs/{config_id}", response_model=EmailConfigRead)
def update_email_config(
    config_id: str,
    payload: EmailConfigUpdate,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    config = db.query(ingestion_models.EmailConfiguration).filter(
        ingestion_models.EmailConfiguration.id == config_id,
        ingestion_models.EmailConfiguration.tenant_id == str(current_user.tenant_id)
    ).first()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    
    # Update fields
    if payload.email is not None: config.email = payload.email
    if payload.password is not None: config.password = payload.password
    if payload.imap_server is not None: config.imap_server = payload.imap_server
    if payload.folder is not None: config.folder = payload.folder
    if payload.user_id is not None: config.user_id = payload.user_id

    if payload.auto_sync_enabled is not None: config.auto_sync_enabled = payload.auto_sync_enabled
    if payload.reset_sync_history:
        config.last_sync_at = None
    if payload.last_sync_at is not None:
        config.last_sync_at = payload.last_sync_at
    
    db.commit()
    db.refresh(config)
    return config

@router.delete("/email/configs/{config_id}")
def delete_email_config(
    config_id: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    config = db.query(ingestion_models.EmailConfiguration).filter(
        ingestion_models.EmailConfiguration.id == config_id,
        ingestion_models.EmailConfiguration.tenant_id == str(current_user.tenant_id)
    ).first()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    db.delete(config)
    db.commit()
    return {"status": "deleted"}

@router.get("/email/logs", response_model=Dict)
def list_email_logs(
    limit: int = 50,
    skip: int = 0,
    config_id: Optional[str] = None,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(ingestion_models.EmailSyncLog).filter(
        ingestion_models.EmailSyncLog.tenant_id == str(current_user.tenant_id)
    )
    if config_id:
        query = query.filter(ingestion_models.EmailSyncLog.config_id == config_id)
        
    total = query.count()
    items = query.order_by(ingestion_models.EmailSyncLog.started_at.desc()).offset(skip).limit(limit).all()
    
    # Convert SQLAlchemy objects to dictionaries to avoid Pydantic serialization errors
    items_data = []
    for item in items:
        items_data.append({
            "id": item.id,
            "config_id": item.config_id,
            "tenant_id": item.tenant_id,
            "started_at": item.started_at,
            "completed_at": item.completed_at,
            "status": item.status,
            "items_processed": item.items_processed,
            "message": item.message
        })

    return {
        "total": total,
        "items": items_data,
        "limit": limit,
        "skip": skip
    }

@router.get("/email/configs/{config_id}/logs", response_model=List[EmailSyncLogRead])
def get_email_sync_logs(
    config_id: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify ownership
    config = db.query(ingestion_models.EmailConfiguration).filter(
        ingestion_models.EmailConfiguration.id == config_id,
        ingestion_models.EmailConfiguration.tenant_id == str(current_user.tenant_id)
    ).first()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")

    return db.query(ingestion_models.EmailSyncLog).filter(
        ingestion_models.EmailSyncLog.config_id == config_id
    ).order_by(ingestion_models.EmailSyncLog.started_at.desc()).limit(10).all()

@router.post("/email/sync/{config_id}")
def sync_specific_email(
    config_id: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    config = db.query(ingestion_models.EmailConfiguration).filter(
        ingestion_models.EmailConfiguration.id == config_id,
        ingestion_models.EmailConfiguration.tenant_id == str(current_user.tenant_id)
    ).first()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    
    criterion = 'ALL' 
    
    result = EmailSyncService.sync_emails(
        db=db,
        tenant_id=str(current_user.tenant_id),
        config_id=config.id,
        imap_server=config.imap_server,
        email_user=config.email,
        email_pass=config.password,
        folder=config.folder,
        search_criterion=criterion,
        since_date=config.last_sync_at
    )
    
    if result.get("status") == "completed":
        config.last_sync_at = datetime.utcnow()
        db.commit()
        
    return result

@router.post("/csv/analyze")
async def analyze_file(
    file: UploadFile = File(...),
    current_user: auth_models.User = Depends(get_current_user)
):
    """
    Auto-detect header row and return preview via External Parser.
    """
    try:
        content = await file.read()
        
        # Call External Parser without mapping to trigger analysis
        from backend.app.modules.ingestion.parser_service import ExternalParserService
        response = ExternalParserService.parse_file(content, file.filename)
        
        # Microservice returns "analysis_required" and puts analysis JSON in logs[0]
        # logic from parser/api/ingestion.py: logs=["No mapping found. Analysis: " + json.dumps(analysis)]
        
        if response and response.get("status") == "analysis_required":
            logs = response.get("logs", [])
            if logs:
                import re
                # Extract JSON from "No mapping found. Analysis: {...}"
                match = re.search(r"Analysis: ({.*})", logs[0])
                if match:
                    return json.loads(match.group(1))
        
        # Fallback or error
        raise HTTPException(status_code=400, detail=f"Analysis failed: {response.get('logs') if response else 'Unknown error'}")

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/csv/parse") 
async def parse_file(
    file: UploadFile = File(...),
    mapping: str = Form(...), # JSON string
    header_row_index: int = Form(0),
    current_user: auth_models.User = Depends(get_current_user)
):
    """
    Parse CSV/Excel and return rows via External Parser.
    """
    try:
        mapping_dict = json.loads(mapping)
        content = await file.read()
        
        from backend.app.modules.ingestion.parser_service import ExternalParserService
        response = ExternalParserService.parse_file(content, file.filename, mapping_dict, header_row_index=header_row_index)
        
        if response:
             if response.get("status") == "success":
                # Transform IngestionResult back to flat list of transactions
                results = response.get("results", [])
                flat_txns = []
                for item in results:
                    txn = item.get("transaction")
                    if txn:
                        flat_txns.append(txn)
                return flat_txns
             else:
                 # Check for logs
                 logs = response.get("logs", [])
                 detail_msg = f"Parsing failed: {logs[0] if logs else 'Unknown error'}"
                 raise HTTPException(status_code=400, detail=detail_msg)
            
        raise HTTPException(status_code=400, detail=f"Parsing failed: {response.get('logs') if response else 'Unknown error'}")

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

class ImportItem(BaseModel):
    date: str
    description: str
    recipient: Optional[str] = None
    amount: float
    type: str # DEBIT/CREDIT
    external_id: Optional[str] = None
    ref_id: Optional[str] = None # Parser returns ref_id
    is_transfer: bool = False
    to_account_id: Optional[str] = None
    balance: Optional[float] = None
    credit_limit: Optional[float] = None

class ImportPayload(BaseModel):
    account_id: str
    transactions: List[ImportItem]
    source: str = "CSV" # Default to CSV

@router.post("/csv/import")
def import_csv(
    payload: ImportPayload,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Bulk import verified transactions.
    """
    success_count = 0
    errors = []
    
    from datetime import datetime
    
    # 1. Fetch Account once
    account = db.query(finance_models.Account).filter(
        finance_models.Account.id == payload.account_id,
        finance_models.Account.tenant_id == str(current_user.tenant_id)
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    for idx, txn in enumerate(payload.transactions):
        try:
             # Convert to Finance Service format
             # Note: Parser already returns negative amounts for DEBIT, positive for CREDIT
             txn_date = datetime.fromisoformat(txn.date)
             
             # --- BALANCE ANCHORING LOGIC ---
             balance_synced = False
             if txn.balance is not None:
                 # Check if this transaction is newer than the current anchor
                 is_newer = True
                 if account.last_synced_at and txn_date < account.last_synced_at:
                     is_newer = False
                 
                 if is_newer:
                     # Update anchor fields
                     account.last_synced_balance = txn.balance
                     account.last_synced_at = txn_date
                     if txn.credit_limit is not None:
                         account.last_synced_limit = txn.credit_limit
                     
                     # Update current running balance
                     account.balance = txn.balance
                     if txn.credit_limit is not None:
                         account.credit_limit = txn.credit_limit
                     
                     # Create snapshot
                     snapshot = finance_models.BalanceSnapshot(
                         account_id=str(account.id),
                         tenant_id=str(current_user.tenant_id),
                         balance=txn.balance,
                         timestamp=txn_date,
                         source=payload.source
                     )
                     db.add(snapshot)
                     # We must commit intermediate updates so subseq txns see the new anchor
                     db.commit() 
                     db.refresh(account)
                     
                     balance_synced = True

             txn_create = finance_schemas.TransactionCreate(
                 account_id=payload.account_id,
                 amount=txn.amount,  # Use parsed amount as-is
                 date=txn_date,
                 description=txn.description,
                 recipient=txn.recipient,  # Extracted merchant/payee
                 category="Uncategorized",
                 tags=[],
                 source=payload.source,
                 external_id=txn.external_id or txn.ref_id
             )
             
             # Pass update_balance=False if we just anchored it
             TransactionService.create_transaction(
                 db, txn_create, str(current_user.tenant_id),
                 update_balance=not balance_synced
             )
             success_count += 1
        except Exception as e:
            errors.append(f"Row {idx+1}: {str(e)}")
            
    IngestionService.log_event(
        db, 
        str(current_user.tenant_id), 
        "bulk_import", 
        "success" if success_count > 0 else "failed",
        f"Imported {success_count} transactions from {payload.source}",
        data={"source": payload.source, "success_count": success_count, "error_count": len(errors), "total": len(payload.transactions)}
    )

    return {
        "status": "completed",
        "imported": success_count,
        "errors": errors
    }

# --- Triage Area ---

class PendingTransactionRead(BaseModel):
    id: str
    tenant_id: str
    account_id: str
    amount: float
    date: datetime
    description: Optional[str] = None
    recipient: Optional[str] = None
    category: Optional[str] = None
    source: str
    raw_message: Optional[str] = None
    external_id: Optional[str] = None
    balance_is_synced: bool = False
    is_transfer: bool = False
    to_account_id: Optional[str] = None
    exclude_from_reports: bool = False
    created_at: datetime

    class Config:
        from_attributes = True

@router.get("/triage")
def list_triage(
    limit: int = 50,
    skip: int = 0,
    sort_by: str = "date",
    sort_order: str = "desc",
    search: Optional[str] = None,
    source: Optional[str] = None,
    user_id: Optional[str] = None,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    items, total = TransactionService.get_pending_transactions(
        db, str(current_user.tenant_id), skip=skip, limit=limit, 
        sort_by=sort_by, sort_order=sort_order, search=search, source=source,
        user_id=user_id
    )
    return {
        "total": total,
        "items": items,
        "limit": limit,
        "skip": skip
    }

class TriageApproveRequest(BaseModel):
    category: Optional[str] = None
    is_transfer: bool = False
    to_account_id: Optional[str] = None
    exclude_from_reports: Optional[bool] = None
    create_rule: bool = False

@router.post("/triage/{pending_id}/approve")
def approve_triage(
    pending_id: str,
    payload: TriageApproveRequest,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    txn = TransactionService.approve_pending_transaction(
        db, 
        pending_id, 
        str(current_user.tenant_id), 
        category_override=payload.category,
        is_transfer_override=payload.is_transfer,
        to_account_id_override=payload.to_account_id,
        exclude_from_reports_override=payload.exclude_from_reports,
        create_rule=payload.create_rule
    )
    if not txn:
        raise HTTPException(status_code=404, detail="Pending transaction not found")
    return {"status": "approved", "transaction_id": txn.id}

@router.delete("/triage/{pending_id}")
def reject_triage(
    pending_id: str,
    create_ignore_rule: bool = False,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    success = TransactionService.reject_pending_transaction(
        db, pending_id, str(current_user.tenant_id), create_ignore_rule=create_ignore_rule
    )
    if not success:
        raise HTTPException(status_code=404, detail="Pending transaction not found")
    return {"status": "rejected"}

class BulkTriageRequest(BaseModel):
    pending_ids: List[str]
    create_ignore_rules: bool = False

@router.post("/triage/bulk-reject")
def bulk_reject_triage(
    payload: BulkTriageRequest,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    count = TransactionService.bulk_reject_pending_transactions(
        db, payload.pending_ids, str(current_user.tenant_id), create_ignore_rules=payload.create_ignore_rules
    )
    return {"status": "deleted", "count": count}

# --- Interactive Training ---

class UnparsedMessageRead(BaseModel):
    id: str
    source: str
    raw_content: str
    subject: Optional[str]
    sender: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

@router.get("/training")
def get_unparsed_messages(
    skip: int = 0,
    limit: int = 20,
    source_filter: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    db: Session = Depends(get_db),
    current_user: auth_models.User = Depends(get_current_user)
):
    query = db.query(ingestion_models.UnparsedMessage).filter(
        ingestion_models.UnparsedMessage.tenant_id == current_user.tenant_id
    )

    if source_filter:
        query = query.filter(ingestion_models.UnparsedMessage.source == source_filter)

    total = query.count()

    # Sort
    if hasattr(ingestion_models.UnparsedMessage, sort_by):
        col = getattr(ingestion_models.UnparsedMessage, sort_by)
        if sort_order == "desc":
            query = query.order_by(col.desc())
        else:
            query = query.order_by(col.asc())
    else:
        query = query.order_by(ingestion_models.UnparsedMessage.created_at.desc())

    items = query.offset(skip).limit(limit).all()

    return {
        "total": total,
        "items": items,
        "limit": limit,
        "skip": skip
    }
# --- Vendor Alias Management ---

class AliasCreate(BaseModel):
    pattern: str
    alias: str
    update_past_transactions: bool = False

class AliasRead(BaseModel):
    id: str
    pattern: str
    alias: str
    created_at: Optional[datetime] = None

class AliasPreviewRequest(BaseModel):
    pattern: str

@router.get("/aliases", response_model=List[Dict[str, Any]])
def list_aliases(
    current_user: auth_models.User = Depends(get_current_user)
):
    """
    Get all merchant aliases from external parser.
    """
    from backend.app.modules.ingestion.parser_service import ExternalParserService
    return ExternalParserService.get_aliases()

@router.post("/aliases")
def create_alias(
    payload: AliasCreate,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new alias rule and optionally update past transactions.
    """
    from backend.app.modules.ingestion.parser_service import ExternalParserService
    
    # 1. Create Rule in Parser
    success = ExternalParserService.create_alias(payload.pattern, payload.alias)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to create alias in parser service")

    updated_count = 0
    if payload.update_past_transactions:
        # 2. Retroactive Update: Find transactions where description or recipient contains pattern
        pattern_wildcard = f"%{payload.pattern}%"
        
        # Update finalized transactions
        txns_to_update = db.query(finance_models.Transaction).filter(
            finance_models.Transaction.tenant_id == str(current_user.tenant_id),
            or_(
                finance_models.Transaction.description.ilike(pattern_wildcard),
                finance_models.Transaction.recipient.ilike(pattern_wildcard)
            )
        ).all()
        
        for txn in txns_to_update:
            txn.recipient = payload.alias
            updated_count += 1

        # Update pending transactions (triage)
        pending_to_update = db.query(ingestion_models.PendingTransaction).filter(
            ingestion_models.PendingTransaction.tenant_id == str(current_user.tenant_id),
            or_(
                ingestion_models.PendingTransaction.description.ilike(pattern_wildcard),
                ingestion_models.PendingTransaction.recipient.ilike(pattern_wildcard)
            )
        ).all()

        for p_txn in pending_to_update:
            p_txn.recipient = payload.alias
            updated_count += 1
            
        db.commit()

    return {"status": "created", "updated_past_transactions": updated_count}

class AliasUpdate(BaseModel):
    pattern: str
    alias: str
    update_past_transactions: bool = False

@router.put("/aliases/{alias_id}")
def update_alias(
    alias_id: str,
    payload: AliasUpdate,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update an existing merchant alias.
    """
    from backend.app.modules.ingestion.parser_service import ExternalParserService
    success = ExternalParserService.update_alias(alias_id, payload.pattern, payload.alias)
    if not success:
        raise HTTPException(status_code=404, detail="Alias not found or failed to update")

    updated_count = 0
    if payload.update_past_transactions:
        # Retroactive Update
        pattern_wildcard = f"%{payload.pattern}%"
        
        # Update finalized transactions
        txns_to_update = db.query(finance_models.Transaction).filter(
            finance_models.Transaction.tenant_id == str(current_user.tenant_id),
            or_(
                finance_models.Transaction.description.ilike(pattern_wildcard),
                finance_models.Transaction.recipient.ilike(pattern_wildcard)
            )
        ).all()
        
        for txn in txns_to_update:
            txn.recipient = payload.alias
            updated_count += 1

        # Update pending transactions (triage)
        pending_to_update = db.query(ingestion_models.PendingTransaction).filter(
            ingestion_models.PendingTransaction.tenant_id == str(current_user.tenant_id),
            or_(
                ingestion_models.PendingTransaction.description.ilike(pattern_wildcard),
                ingestion_models.PendingTransaction.recipient.ilike(pattern_wildcard)
            )
        ).all()

        for p_txn in pending_to_update:
            p_txn.recipient = payload.alias
            updated_count += 1
            
        db.commit()

    return {"status": "updated", "updated_past_transactions": updated_count}

@router.post("/aliases/preview")
def preview_alias_impact(
    payload: AliasPreviewRequest,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check how many past transactions would match this pattern.
    """
    pattern_wildcard = f"%{payload.pattern}%"
    
    count_finalized = db.query(finance_models.Transaction).filter(
        finance_models.Transaction.tenant_id == str(current_user.tenant_id),
        or_(
            finance_models.Transaction.description.ilike(pattern_wildcard),
            finance_models.Transaction.recipient.ilike(pattern_wildcard)
        )
    ).count()

    count_pending = db.query(ingestion_models.PendingTransaction).filter(
        ingestion_models.PendingTransaction.tenant_id == str(current_user.tenant_id),
        or_(
            ingestion_models.PendingTransaction.description.ilike(pattern_wildcard),
            ingestion_models.PendingTransaction.recipient.ilike(pattern_wildcard)
        )
    ).count()
    
    return {"match_count": count_finalized + count_pending}

@router.delete("/aliases/{alias_id}")
def delete_alias(
    alias_id: str,
    current_user: auth_models.User = Depends(get_current_user)
):
    """
    Delete an alias rule.
    """
    from backend.app.modules.ingestion.parser_service import ExternalParserService
    success = ExternalParserService.delete_alias(alias_id)
    if not success:
        raise HTTPException(status_code=404, detail="Alias not found or failed to delete")
    return {"status": "deleted"}


class LabelPayload(BaseModel):
    amount: float
    date: datetime
    account_mask: str
    recipient: Optional[str]
    category: Optional[str] = "Uncategorized"
    ref_id: Optional[str]
    balance: Optional[float] = None
    credit_limit: Optional[float] = None
    type: str = "DEBIT" # DEBIT or CREDIT
    generate_pattern: bool = True
    exclude_from_reports: bool = False

@router.post("/training/{message_id}/label")
def label_message(
    message_id: str,
    payload: LabelPayload,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    msg = db.query(ingestion_models.UnparsedMessage).filter(
        ingestion_models.UnparsedMessage.id == message_id,
        ingestion_models.UnparsedMessage.tenant_id == str(current_user.tenant_id)
    ).first()
    
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
        
    # Promote to PendingTransaction
    account = IngestionService.match_account(db, str(current_user.tenant_id), payload.account_mask)
    if not account:
        # Create auto-account if mask provided
        account = finance_models.Account(
            tenant_id=str(current_user.tenant_id),
            name=f"Detected: (XX{payload.account_mask[-4:]})",
            type=finance_models.AccountType.BANK,
            account_mask=payload.account_mask[-4:],
            is_verified=False,
            balance=0.0
        )
        db.add(account)
        db.commit()
        db.refresh(account)

    effective_ref = payload.ref_id
    if not effective_ref:
        date_str = payload.date.strftime("%Y%m%d%H%M%S")
        effective_ref = f"MAN-{date_str}-{payload.account_mask}-{payload.amount:.2f}"

    # Determine effective amount based on type
    effective_amount = payload.amount
    if payload.type == "DEBIT":
        effective_amount = -abs(payload.amount)
    else:
        effective_amount = abs(payload.amount)

    # If balance/limit provided in label, anchor it
    if payload.balance is not None:
        # Check if this is the "New Reality" (newer or same as current anchor)
        is_newer = True
        if account.last_synced_at and payload.date < account.last_synced_at:
            is_newer = False
            
        if is_newer:
            account.balance = payload.balance
            account.last_synced_balance = payload.balance
            account.last_synced_at = payload.date
            if payload.credit_limit is not None:
                account.credit_limit = payload.credit_limit
                account.last_synced_limit = payload.credit_limit
        
        # Always create snapshot as it stores ground truth for the specific point in time
        db.add(finance_models.BalanceSnapshot(
            account_id=str(account.id),
            tenant_id=str(current_user.tenant_id),
            balance=payload.balance,
            timestamp=payload.date,
            source="MANUAL_TRAINING"
        ))

    pending = ingestion_models.PendingTransaction(
        tenant_id=str(current_user.tenant_id),
        account_id=str(account.id),
        amount=effective_amount,
        date=payload.date,
        description=f"Learned: {payload.recipient or 'Unknown'}",
        recipient=payload.recipient,
        category=payload.category or "Uncategorized",
        source=msg.source,
        raw_message=msg.raw_content,
        external_id=effective_ref,
        balance_is_synced=(payload.balance is not None),
        exclude_from_reports=payload.exclude_from_reports
    )
    db.add(pending)
    
    # Pattern Generation Logic
    # Pattern Generation Logic
    if payload.generate_pattern:
        try:
            pattern_str, mapping_json = PatternGenerator.generate_regex_and_config(msg.raw_content, payload.dict(), txn_type=payload.type)
            
            # Send to External Parser Service
            from backend.app.modules.ingestion.parser_service import ExternalParserService
            import json
            
            ExternalParserService.create_pattern(
                source=msg.source,
                regex_pattern=pattern_str,
                mapping=json.loads(mapping_json)
            )
            # Legacy local save removed to enforce single source of truth
        except Exception as e:
            logger.error(f"Error creating pattern: {e}")
            pass
        
    db.delete(msg)
    db.commit()
    
    return {"status": "labeled", "pending_id": pending.id}

@router.delete("/training/{message_id}")
def dismiss_training_message(
    message_id: str,
    create_ignore_rule: bool = False,
    ignore_pattern: Optional[str] = None,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    msg = db.query(ingestion_models.UnparsedMessage).filter(
        ingestion_models.UnparsedMessage.id == message_id,
        ingestion_models.UnparsedMessage.tenant_id == str(current_user.tenant_id)
    ).first()
    
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
        
    if create_ignore_rule:
        pattern = ignore_pattern or msg.subject or msg.raw_content[:30]
        if pattern:
             existing = db.query(ingestion_models.IgnoredPattern).filter(
                ingestion_models.IgnoredPattern.tenant_id == str(current_user.tenant_id),
                ingestion_models.IgnoredPattern.pattern == pattern
            ).first()
             if not existing:
                new_ignore = ingestion_models.IgnoredPattern(
                    tenant_id=str(current_user.tenant_id),
                    pattern=pattern,
                    source=msg.source
                )
                db.add(new_ignore)

    db.delete(msg)
    db.commit()
    return {"status": "dismissed"}

class BulkTrainingRequest(BaseModel):
    message_ids: List[str]
    create_ignore_rules: bool = False
    # For bulk, we don't easily support custom patterns per item here, 
    # so we'll just use the subjects/prefixes of the selected items.

@router.post("/training/bulk-dismiss")
def bulk_dismiss_training(
    payload: BulkTrainingRequest,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if payload.create_ignore_rules:
        msgs = db.query(ingestion_models.UnparsedMessage).filter(
            ingestion_models.UnparsedMessage.id.in_(payload.message_ids),
            ingestion_models.UnparsedMessage.tenant_id == str(current_user.tenant_id)
        ).all()
        for m in msgs:
            pattern = m.subject or m.raw_content[:30]
            if pattern:
                existing = db.query(ingestion_models.IgnoredPattern).filter(
                    ingestion_models.IgnoredPattern.tenant_id == str(current_user.tenant_id),
                    ingestion_models.IgnoredPattern.pattern == pattern
                ).first()
                if not existing:
                    db.add(ingestion_models.IgnoredPattern(
                        tenant_id=str(current_user.tenant_id),
                        pattern=pattern,
                        source=m.source
                    ))

    count = db.query(ingestion_models.UnparsedMessage).filter(
        ingestion_models.UnparsedMessage.id.in_(payload.message_ids),
        ingestion_models.UnparsedMessage.tenant_id == str(current_user.tenant_id)
    ).delete(synchronize_session=False)
    db.commit()
    return {"status": "deleted", "count": count}

@router.post("/ai/sync-to-parser")
def sync_ai_to_parser(
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Push the main app's AI configuration to the parser microservice.
    """
    from backend.app.modules.ingestion.ai_service import AIService
    from backend.app.modules.ingestion.parser_service import ExternalParserService
    
    tenant_id = str(current_user.tenant_id)
    settings_data = AIService.get_settings(db, tenant_id)
    if not settings_data:
        raise HTTPException(status_code=404, detail="AI Settings not found")
    
    raw_key = AIService.get_raw_api_key(db, tenant_id)
    
    success = ExternalParserService.sync_ai_config(
        api_key=raw_key or "",
        model_name=settings_data.get("model_name", "gemini-pro"),
        is_enabled=settings_data.get("is_enabled", False)
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to sync with parser microservice")
    
    return {"status": "synced"}

# --- Auditing / Events ---

class IngestionEventRead(BaseModel):
    id: str
    device_id: Optional[str]
    event_type: str
    status: str
    message: Optional[str]
    data_json: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

@router.get("/events")
def list_ingestion_events(
    limit: int = 50,
    skip: int = 0,
    device_id: Optional[str] = None,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(ingestion_models.IngestionEvent).filter(
        ingestion_models.IngestionEvent.tenant_id == str(current_user.tenant_id)
    )
    if device_id:
        query = query.filter(ingestion_models.IngestionEvent.device_id == device_id)
    
    total = query.count()
    items = query.order_by(ingestion_models.IngestionEvent.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "items": items,
        "limit": limit,
        "skip": skip
    }

class BulkDeleteEventsRequest(BaseModel):
    event_ids: List[str]

@router.post("/events/bulk-delete")
def bulk_delete_events(
    payload: BulkDeleteEventsRequest,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db.query(ingestion_models.IngestionEvent).filter(
        ingestion_models.IngestionEvent.id.in_(payload.event_ids),
        ingestion_models.IngestionEvent.tenant_id == str(current_user.tenant_id)
    ).delete(synchronize_session=False)
    db.commit()
    return {"status": "deleted", "count": len(payload.event_ids)}
