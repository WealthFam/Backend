from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import os
from datetime import datetime

from backend.app.core.database import get_db
from backend.app.modules.auth.dependencies import get_current_user
from backend.app.modules.auth.models import User
from backend.app.modules.finance import models as finance_models
from backend.app.modules.finance import schemas as finance_schemas
from backend.app.modules.ingestion.statement_processor import StatementProcessor
from backend.app.modules.vault.service import VaultService

router = APIRouter(prefix="/statements", tags=["Statements"], redirect_slashes=False)

@router.get("", response_model=finance_schemas.PaginatedStatementRead)
def list_statements(
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List processed statements for the tenant with pagination.
    """
    from backend.app.modules.auth.models import UserRole
    if current_user.role == UserRole.CHILD:
        return {"items": [], "total": 0}
    
    query = db.query(finance_models.Statement).filter(
        finance_models.Statement.tenant_id == current_user.tenant_id,
        finance_models.Statement.is_deleted == False
    )
    
    if search:
        query = query.filter(finance_models.Statement.filename.ilike(f"%{search}%"))
        
    total = query.count()
    statements = query.order_by(finance_models.Statement.created_at.desc()).offset(skip).limit(limit).all()
    return {"items": statements, "total": total}

@router.post("/upload")
async def upload_statement(
    file: UploadFile = File(...),
    password: Optional[str] = Form(None),
    account_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually upload a bank statement PDF.
    """
    content = await file.read()
    try:
        # If password is provided, we use it. Otherwise, processor will try trials.
        statement = await StatementProcessor.process_statement_file(
            db, str(current_user.tenant_id), 
            file.filename, content, source="MANUAL",
            account_id=account_id,
            manual_password=password,
            email_sender=current_user.email
        )
        
        if statement.status == finance_models.StatementStatus.PARSED:
            return {"status": "success", "message": "Statement uploaded and parsed successfully."}
        else:
            return {"status": "pending", "message": "Statement uploaded but decryption failed. Please check the 'Pending' tab to provide the password manually."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{statement_id}/transactions", response_model=finance_schemas.PaginatedStatementTransactionRead)
def get_statement_transactions(
    statement_id: str,
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get transactions extracted from a specific statement with pagination.
    """
    # Verify ownership
    statement = db.query(finance_models.Statement).filter(
        finance_models.Statement.id == statement_id,
        finance_models.Statement.tenant_id == current_user.tenant_id,
        finance_models.Statement.is_deleted == False
    ).first()
    
    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found")
        
    query = db.query(finance_models.StatementTransaction).filter(
        finance_models.StatementTransaction.statement_id == statement_id,
        finance_models.StatementTransaction.tenant_id == current_user.tenant_id,
        finance_models.StatementTransaction.is_deleted == False
    )
    
    if search:
        query = query.filter(finance_models.StatementTransaction.description.ilike(f"%{search}%"))
        
    total = query.count()
    transactions = query.order_by(finance_models.StatementTransaction.date.asc()).offset(skip).limit(limit).all()
    
    return {"items": transactions, "total": total}

@router.delete("/{statement_id}")
def delete_statement(
    statement_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a statement and its associated transactions and vault file.
    """
    try:
        StatementProcessor.delete_statement(db, str(current_user.tenant_id), statement_id)
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete statement: {str(e)}")

@router.post("/sync")
async def trigger_sync(
    background_tasks: BackgroundTasks,
    since_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually trigger an email scan for statements.
    Run in background to avoid timeouts.
    """
    parsed_date = None
    if since_date:
        try:
            parsed_date = datetime.fromisoformat(since_date)
        except:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
            
    background_tasks.add_task(StatementProcessor.sync_statements, db, str(current_user.tenant_id), since_date=parsed_date)
    return {"status": "success", "message": "Sync triggered in background."}

@router.patch("/{statement_id}", response_model=finance_schemas.StatementRead)
async def update_statement(
    statement_id: str,
    update_data: finance_schemas.StatementUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update statement details (e.g., re-link to a different account).
    """
    try:
        return await StatementProcessor.update_statement(
            db, str(current_user.tenant_id), statement_id, update_data
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update statement: {str(e)}")

@router.post("/{statement_id}/reconcile")
def manual_reconcile(
    statement_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually trigger reconciliation for a statement.
    """
    StatementProcessor.reconcile_statement(db, statement_id)
    return {"status": "success"}

@router.post("/{statement_id}/reprocess")
async def manual_reprocess(
    statement_id: str,
    password: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually trigger a full re-parse of a statement.
    If it's PENDING/FAILED due to password, provide the 'password' query param.
    """
    try:
        return await StatementProcessor.retry_statement(db, str(current_user.tenant_id), statement_id, password or "", email_sender=current_user.email)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/transactions/{transaction_id}/ingest", response_model=finance_schemas.TransactionRead)
def ingest_statement_transaction(
    transaction_id: str,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Convert a statement transaction into a real ledger transaction.
    """
    st_txn = db.query(finance_models.StatementTransaction).filter(
        finance_models.StatementTransaction.id == transaction_id,
        finance_models.StatementTransaction.tenant_id == current_user.tenant_id,
        finance_models.StatementTransaction.is_deleted == False
    ).first()
    
    if not st_txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
        
    if st_txn.is_reconciled:
        raise HTTPException(status_code=400, detail="Transaction already reconciled")
        
    # Create ledger transaction
    from backend.app.modules.finance.services.transaction_service import TransactionService
    from backend.app.modules.finance import schemas as finance_schemas
    
    # Statement amounts are absolute, sign depends on type
    amount = st_txn.amount if st_txn.type == finance_models.TransactionType.CREDIT else -st_txn.amount
    
    txn_create = finance_schemas.TransactionCreate(
        account_id=st_txn.statement.account_id,
        amount=amount,
        date=st_txn.date,
        description=st_txn.description,
        category=category or st_txn.category_suggestion or "Uncategorized",
        source="STATEMENT",
        external_id=st_txn.ref_id
    )
    
    ledger_txn = TransactionService.create_transaction(db, txn_create, str(current_user.tenant_id))
    
    # Mark as reconciled
    st_txn.is_reconciled = True
    st_txn.matched_transaction_id = ledger_txn.id
    db.commit()
    
    return ledger_txn

@router.post("/transactions/bulk-ingest")
def bulk_ingest_statement_transactions(
    request: finance_schemas.BulkIngestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Convert multiple statement transactions into real ledger transactions.
    Optionally create category rules.
    """
    from backend.app.modules.finance.services.transaction_service import TransactionService
    from backend.app.modules.finance.services.category_service import CategoryService
    from backend.app.modules.finance import schemas as finance_schemas

    tenant_id = str(current_user.tenant_id)
    ingested_count = 0
    
    for item in request.items:
        st_txn = db.query(finance_models.StatementTransaction).filter(
            finance_models.StatementTransaction.id == item.transaction_id,
            finance_models.StatementTransaction.tenant_id == tenant_id
        ).first()
        
        if not st_txn or st_txn.is_reconciled or st_txn.is_deleted:
            continue
            
        # 1. Create Rule if requested
        if item.create_rule and item.category and st_txn.description:
            # Check if rule already exists (using a slightly more robust check)
            search_pattern = json.dumps(st_txn.description)
            existing_rule = db.query(finance_models.CategoryRule).filter(
                finance_models.CategoryRule.tenant_id == tenant_id,
                finance_models.CategoryRule.keywords.like(f'%{search_pattern}%')
            ).first()
            
            if not existing_rule:
                rule_create = finance_schemas.CategoryRuleCreate(
                    name=f"Rule for {st_txn.description[:20]}...",
                    category=item.category,
                    keywords=[st_txn.description],
                    priority=10
                )
                CategoryService.create_category_rule(db, rule_create, tenant_id, commit=False)
        
        # 2. Create ledger transaction
        amount = st_txn.amount if st_txn.type == finance_models.TransactionType.CREDIT else -st_txn.amount
        
        txn_create = finance_schemas.TransactionCreate(
            account_id=st_txn.statement.account_id,
            amount=amount,
            date=st_txn.date,
            description=st_txn.description,
            category=item.category or "Uncategorized",
            source="STATEMENT",
            external_id=st_txn.ref_id,
            exclude_from_reports=item.exclude_from_reports
        )
        
        ledger_txn = TransactionService.create_transaction(db, txn_create, tenant_id, commit=False)
        
        # 3. Mark as reconciled
        st_txn.is_reconciled = True
        st_txn.matched_transaction_id = ledger_txn.id
        ingested_count += 1
        
    db.commit()
    return {"status": "success", "ingested_count": ingested_count}
