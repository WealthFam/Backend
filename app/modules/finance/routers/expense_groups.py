from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.modules.auth import models as auth_models
from backend.app.modules.auth.dependencies import get_current_user
from backend.app.modules.finance import schemas
from backend.app.modules.finance.services.expense_group_service import ExpenseGroupService

router = APIRouter()

@router.get("/expense-groups", response_model=List[schemas.ExpenseGroupRead])
def get_expense_groups(
    user_id: str | None = None,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return ExpenseGroupService.get_expense_groups(db, str(current_user.tenant_id), user_id)

@router.post("/expense-groups", response_model=schemas.ExpenseGroupRead)
def create_expense_group(
    group: schemas.ExpenseGroupCreate,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return ExpenseGroupService.create_expense_group(db, group, str(current_user.tenant_id))

@router.put("/expense-groups/{group_id}", response_model=schemas.ExpenseGroupRead)
def update_expense_group(
    group_id: str,
    update: schemas.ExpenseGroupUpdate,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    group = ExpenseGroupService.update_expense_group(db, group_id, update, str(current_user.tenant_id))
    if not group:
        raise HTTPException(status_code=404, detail="Expense group not found")
    return group

@router.delete("/expense-groups/{group_id}")
def delete_expense_group(
    group_id: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not ExpenseGroupService.delete_expense_group(db, group_id, str(current_user.tenant_id)):
        raise HTTPException(status_code=404, detail="Expense group not found")
    return {"status": "success"}

@router.post("/expense-groups/{group_id}/transactions")
def link_transactions_to_group(
    group_id: str,
    payload: schemas.BulkLinkTransactionsRequest,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    count = ExpenseGroupService.link_transactions(
        db, group_id, payload.transaction_ids, str(current_user.tenant_id)
    )
    if count == 0:
        # Could be 0 because group not found or no transactions matched
        # For simplicity, we check if group exists in service anyway
        pass
    return {"status": "success", "linked_count": count}
