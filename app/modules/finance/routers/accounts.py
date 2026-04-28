import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.modules.auth import models as auth_models
from backend.app.modules.auth.dependencies import get_current_user
from backend.app.modules.finance import schemas
from backend.app.modules.finance.services.account_service import AccountService
from backend.app.modules.finance.services.transaction_service import TransactionService

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/accounts", response_model=schemas.AccountRead)
def create_account(
    account: schemas.AccountCreate,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if account.owner_id is None:
        account.owner_id = current_user.id
    return AccountService.create_account(db, account, str(current_user.tenant_id))

@router.get("/accounts", response_model=List[schemas.AccountRead])
def read_accounts(
    user_id: Optional[str] = None,
    include_unverified: bool = False,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return AccountService.get_accounts(
        db, 
        str(current_user.tenant_id), 
        owner_id=user_id, 
        user_role=current_user.role,
        include_unverified=include_unverified
    )

@router.put("/accounts/{account_id}", response_model=schemas.AccountRead)
def update_account(
    account_id: str,
    account_update: schemas.AccountUpdate,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_account = AccountService.update_account(
        db, account_id, account_update, str(current_user.tenant_id)
    )
    if not db_account:
        raise HTTPException(status_code=404, detail="Account not found")
    return db_account

@router.delete("/accounts/{account_id}")
def delete_account(
    account_id: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if "CHILD" in str(current_user.role).upper():
        raise HTTPException(status_code=403, detail="Children are not allowed to delete accounts")

    success = AccountService.delete_account(
        db, account_id, str(current_user.tenant_id)
    )
    if not success:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"status": "success", "message": "Account and related transactions deleted"}

@router.get("/accounts/{account_id}/transaction-count")
def get_account_transaction_count(
    account_id: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    count = TransactionService.count_transactions(
        db, str(current_user.tenant_id), account_id, user_role=current_user.role
    )
    return {"count": count}

@router.put("/accounts/{account_id}/balance")
def update_account_balance(
    account_id: str,
    payload: schemas.BalanceSnapshotBase,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        return AccountService.override_balance(
            db, account_id, float(payload.balance), payload.timestamp, str(current_user.tenant_id), 
            credit_limit=float(payload.credit_limit) if payload.credit_limit is not None else None,
            source=payload.source
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/accounts/{account_id}/pay-bill")
def pay_credit_bill(
    account_id: str,
    payload: schemas.CreditCardBillPay,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        return AccountService.pay_credit_bill(
            db, account_id, payload, str(current_user.tenant_id)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
