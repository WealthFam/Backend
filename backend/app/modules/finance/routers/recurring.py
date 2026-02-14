from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.modules.auth import models as auth_models
from backend.app.modules.auth.dependencies import get_current_user
from backend.app.modules.finance import schemas
from backend.app.modules.finance.services.recurring_service import RecurringService

router = APIRouter()

@router.post("/recurring", response_model=schemas.RecurringTransactionRead)
def create_recurring_transaction(
    recurrence: schemas.RecurringTransactionCreate,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return RecurringService.create_recurring_transaction(db, recurrence, str(current_user.tenant_id))

@router.get("/recurring", response_model=List[schemas.RecurringTransactionRead])
def get_recurring_transactions(
    user_id: str = None,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return RecurringService.get_recurring_transactions(db, str(current_user.tenant_id), user_id=user_id)

@router.put("/recurring/{recurrence_id}", response_model=schemas.RecurringTransactionRead)
def update_recurring_transaction(
    recurrence_id: str,
    update: schemas.RecurringTransactionUpdate,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    rec = RecurringService.update_recurring_transaction(db, recurrence_id, update, str(current_user.tenant_id))
    if not rec: raise HTTPException(status_code=404, detail="Recurring transaction not found")
    return rec

@router.delete("/recurring/{recurrence_id}")
def delete_recurring_transaction(
    recurrence_id: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    success = RecurringService.delete_recurring_transaction(db, recurrence_id, str(current_user.tenant_id))
    if not success: raise HTTPException(status_code=404, detail="Recurring transaction not found")
    return {"status": "success"}

@router.post("/recurring/process")
def process_recurring_transactions(
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    count = RecurringService.process_recurring_transactions(db, str(current_user.tenant_id))
    return {"status": "success", "processed_count": count}
