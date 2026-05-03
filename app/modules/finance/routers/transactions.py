from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.modules.auth import models as auth_models
from backend.app.modules.auth.dependencies import get_current_user
from backend.app.modules.finance import schemas
from backend.app.modules.finance.services.transaction_service import TransactionService

router = APIRouter()

@router.post("/transactions", response_model=schemas.TransactionRead)
def create_transaction(
    transaction: schemas.TransactionCreate,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        return TransactionService.create_transaction(db, transaction, str(current_user.tenant_id))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/transactions", response_model=schemas.TransactionPagination)
def get_transactions(
    page: int = 1,
    limit: int = 20,
    account_id: Optional[str] = None,
    search: Optional[str] = None,
    category: Optional[str] = None,
    sort_by: Optional[str] = "date",
    sort_order: Optional[str] = "desc",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user_id: Optional[str] = None,
    exclude_from_reports: bool = False,
    exclude_transfers: bool = False,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    skip = (page - 1) * limit
    
    
    s_date = datetime.fromisoformat(start_date) if start_date and start_date.strip() else None
    e_date = datetime.fromisoformat(end_date) if end_date and end_date.strip() else None

    items = TransactionService.get_transactions(
        db, str(current_user.tenant_id), account_id, skip, limit, s_date, e_date, 
        search=search, category=category, user_role=current_user.role,
        sort_by=sort_by, sort_order=sort_order, user_id=user_id,
        exclude_from_reports=exclude_from_reports, exclude_transfers=exclude_transfers
    )
    total = TransactionService.count_transactions(
        db, str(current_user.tenant_id), account_id, s_date, e_date, 
        search=search, category=category, user_role=current_user.role, user_id=user_id,
        exclude_from_reports=exclude_from_reports, exclude_transfers=exclude_transfers
    )
    
    return {
        "data": items,
        "total": total,
        "page": page,
        "size": limit
    }

@router.get("/transactions/{transaction_id}", response_model=schemas.TransactionRead)
def get_transaction(
    transaction_id: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_txn = TransactionService.get_transaction(db, transaction_id, str(current_user.tenant_id))
    if not db_txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return db_txn

@router.post("/transactions/bulk-delete")
def bulk_delete_transactions(
    payload: schemas.BulkDeleteRequest,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    count = TransactionService.bulk_delete_transactions(db, payload.transaction_ids, str(current_user.tenant_id))
    return {"message": f"Deleted {count} transactions", "count": count}

@router.put("/transactions/{transaction_id}", response_model=schemas.TransactionRead)
def update_transaction(
    transaction_id: str,
    transaction_update: schemas.TransactionUpdate,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_txn = TransactionService.update_transaction(
        db, transaction_id, transaction_update, str(current_user.tenant_id)
    )
    if not db_txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return db_txn

@router.get("/transactions/stats/vendor")
def get_vendor_stats(
    vendor_name: str,
    skip: int = 0,
    limit: int = 3,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return TransactionService.get_vendor_stats(db, str(current_user.tenant_id), vendor_name, user_id=None, skip=skip, limit=limit)

@router.post("/transactions/smart-categorize")
def smart_categorize_transaction(
    payload: schemas.SmartCategorizeRequest,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return TransactionService.batch_update_category_and_create_rule(
        db, 
        payload.transaction_id, 
        payload.category, 
        str(current_user.tenant_id),
        create_rule=payload.create_rule,
        apply_to_similar=payload.apply_to_similar,
        exclude_from_reports=payload.exclude_from_reports,
        is_transfer=payload.is_transfer,
        to_account_id=payload.to_account_id
    )

@router.post("/transactions/rules/{rule_id}/apply-retrospective")
def apply_rule_retrospectively(
    rule_id: str,
    override: bool = False,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return TransactionService.apply_rule_retrospectively(db, rule_id, str(current_user.tenant_id), override=override)

@router.post("/transactions/match-count")
def get_match_count(
    payload: schemas.MatchCountRequest,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    count = TransactionService.get_matching_count(
        db, payload.keywords, str(current_user.tenant_id), only_uncategorized=payload.only_uncategorized
    )
    return {"count": count}

@router.post("/transactions/match-preview", response_model=List[schemas.TransactionRead])
def get_match_preview(
    payload: schemas.MatchCountRequest,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = 1,
    limit: int = 5
):
    skip = (page - 1) * limit
    return TransactionService.get_matching_preview(
        db, payload.keywords, str(current_user.tenant_id), skip=skip, limit=limit, only_uncategorized=payload.only_uncategorized
    )

@router.delete("/transactions/{transaction_id}")
def delete_transaction(
    transaction_id: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    count = TransactionService.bulk_delete_transactions(db, [transaction_id], str(current_user.tenant_id))
    if count == 0:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"status": "success"}

@router.post("/transactions/bulk-rename")
def bulk_rename_transactions(
    payload: schemas.BulkRenameRequest,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    count = TransactionService.bulk_rename(
        db, payload.old_name, payload.new_name, str(current_user.tenant_id), payload.sync_to_parser
    )
    return {"message": f"Renamed {count} transactions", "count": count}
