from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.modules.auth import models as auth_models
from backend.app.modules.auth.dependencies import get_current_user
from backend.app.modules.finance import schemas
from backend.app.modules.finance.services.investment_goal_service import InvestmentGoalService

router = APIRouter()

@router.get("/investment-goals", response_model=List[schemas.InvestmentGoalProgress])
def get_goals(
    user_id: Optional[str] = None,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return InvestmentGoalService.get_goals(db, str(current_user.tenant_id), user_id=user_id)

@router.post("/investment-goals", response_model=schemas.InvestmentGoalRead)
def create_goal(
    goal: schemas.InvestmentGoalCreate,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return InvestmentGoalService.create_goal(db, goal, str(current_user.tenant_id))

@router.put("/investment-goals/{goal_id}", response_model=schemas.InvestmentGoalRead)
def update_goal(
    goal_id: str,
    update: schemas.InvestmentGoalUpdate,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    goal = InvestmentGoalService.update_goal(db, goal_id, update, str(current_user.tenant_id))
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal

@router.delete("/investment-goals/{goal_id}")
def delete_goal(
    goal_id: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not InvestmentGoalService.delete_goal(db, goal_id, str(current_user.tenant_id)):
        raise HTTPException(status_code=404, detail="Goal not found")
    return {"status": "success"}

@router.post("/investment-goals/{goal_id}/holdings/{holding_id}")
def link_holding(
    goal_id: str,
    holding_id: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not InvestmentGoalService.link_holding_to_goal(db, holding_id, goal_id, str(current_user.tenant_id)):
        raise HTTPException(status_code=404, detail="Holding or Goal not found")
    return {"status": "success"}

@router.delete("/investment-goals/{goal_id}/holdings/{holding_id}")
def unlink_holding(
    goal_id: str,
    holding_id: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not InvestmentGoalService.link_holding_to_goal(db, holding_id, None, str(current_user.tenant_id)):
        raise HTTPException(status_code=404, detail="Holding not found")
    return {"status": "success"}

@router.post("/investment-goals/{goal_id}/assets", response_model=schemas.GoalAssetRead)
def add_asset(
    goal_id: str,
    asset: schemas.GoalAssetCreate,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_asset = InvestmentGoalService.add_asset(db, goal_id, asset, str(current_user.tenant_id))
    if not db_asset:
        raise HTTPException(status_code=404, detail="Goal not found")
    return db_asset

@router.delete("/investment-goals/assets/{asset_id}")
def remove_asset(
    asset_id: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not InvestmentGoalService.remove_asset(db, asset_id, str(current_user.tenant_id)):
        raise HTTPException(status_code=404, detail="Asset not found")
    return {"status": "success"}
