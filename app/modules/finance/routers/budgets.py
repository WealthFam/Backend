
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.modules.auth import models as auth_models
from backend.app.modules.auth.dependencies import get_current_user
from backend.app.modules.finance import schemas
from backend.app.modules.finance.services.budget_service import BudgetService

router = APIRouter()

@router.get("/budgets", response_model=List[schemas.CategoryBudgetProgress])
@router.get("/budgets/progress", response_model=List[schemas.CategoryBudgetProgress])
def get_budgets(
    year: int = None,
    month: int = None,
    user_id: str = None,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return BudgetService.get_budgets(db, str(current_user.tenant_id), year=year, month=month, user_id=user_id)

@router.get("/budgets/overview", response_model=schemas.BudgetOverview)
def get_budget_overview(
    year: int = None,
    month: int = None,
    user_id: str = None,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return BudgetService.get_budget_overview(db, str(current_user.tenant_id), year=year, month=month, user_id=user_id)

@router.post("/budgets", response_model=schemas.BudgetRead)
def set_budget(
    budget: schemas.BudgetCreate,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return BudgetService.set_budget(db, budget, str(current_user.tenant_id))

@router.delete("/budgets/{budget_id}")
def delete_budget(
    budget_id: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    success = BudgetService.delete_budget(db, budget_id, str(current_user.tenant_id))
    if not success:
        raise HTTPException(status_code=404, detail="Budget not found")
    return {"status": "success"}

@router.get("/budgets/insights")
def get_ai_insights(
    year: int = None,
    month: int = None,
    user_id: str = None,
    force_refresh: bool = False,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return BudgetService.get_ai_insights(db, str(current_user.tenant_id), year=year, month=month, user_id=user_id, force_refresh=force_refresh)
    
@router.get("/budgets/recommendation/{category}")
def get_budget_recommendation(
    category: str,
    force_refresh: bool = False,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return BudgetService.get_budget_recommendation(db, str(current_user.tenant_id), category, force_refresh=force_refresh)
