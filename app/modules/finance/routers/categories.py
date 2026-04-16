from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.modules.auth import models as auth_models
from backend.app.modules.auth.dependencies import get_current_user
from backend.app.modules.finance import schemas
from backend.app.modules.finance.services.category_service import CategoryService

router = APIRouter()

# --- Categories ---
@router.post("/rules/suggestions/ignore")
def ignore_suggestion(
    data: schemas.IgnoredSuggestionCreate,
    db: Session = Depends(get_db),
    current_user: auth_models.User = Depends(get_current_user)
):
    CategoryService.ignore_suggestion(db, data.pattern, str(current_user.tenant_id))
    return {"status": "ignored", "pattern": data.pattern}

@router.get("/categories", response_model=List[schemas.CategoryRead])
def get_categories(
    tree: bool = False,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return CategoryService.get_categories(db, str(current_user.tenant_id), tree=tree)

@router.post("/categories", response_model=schemas.CategoryRead)
def create_category(
    category: schemas.CategoryCreate,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return CategoryService.create_category(db, category, str(current_user.tenant_id))

@router.put("/categories/{category_id}", response_model=schemas.CategoryRead)
def update_category(
    category_id: str,
    update: schemas.CategoryUpdate,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cat = CategoryService.update_category(db, category_id, update, str(current_user.tenant_id))
    if not cat: raise HTTPException(status_code=404, detail="Category not found")
    return cat

@router.delete("/categories/{category_id}")
def delete_category(
    category_id: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    success = CategoryService.delete_category(db, category_id, str(current_user.tenant_id))
    if not success: raise HTTPException(status_code=404, detail="Category not found")
    return {"status": "success"}

@router.post("/categories/import")
def import_categories(
    categories: List[dict],
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    CategoryService.import_categories(db, categories, str(current_user.tenant_id))
    return {"status": "success", "count": len(categories)}

@router.get("/categories/export")
def export_categories(
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return CategoryService.export_categories(db, str(current_user.tenant_id))

# --- Rules ---
@router.post("/rules", response_model=schemas.CategoryRuleRead)
def create_rule(
    rule: schemas.CategoryRuleCreate,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return CategoryService.create_category_rule(db, rule, str(current_user.tenant_id))

@router.get("/rules", response_model=schemas.CategoryRulePagination)
def get_rules(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return CategoryService.get_category_rules(db, str(current_user.tenant_id), skip=skip, limit=limit)

@router.get("/rules/suggestions", response_model=List[schemas.RuleSuggestion])
def get_rule_suggestions(
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return CategoryService.get_rule_suggestions(db, str(current_user.tenant_id))

@router.put("/rules/{rule_id}", response_model=schemas.CategoryRuleRead)
def update_rule(
    rule_id: str,
    rule_update: schemas.CategoryRuleUpdate,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_rule = CategoryService.update_category_rule(db, rule_id, rule_update, str(current_user.tenant_id))
    if not db_rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return db_rule

@router.delete("/rules/{rule_id}")
def delete_rule(
    rule_id: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    success = CategoryService.delete_category_rule(db, rule_id, str(current_user.tenant_id))
    if not success:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"status": "success"}

@router.post("/rules/import")
def import_rules(
    rules: List[dict],
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    CategoryService.import_category_rules(db, rules, str(current_user.tenant_id))
    return {"status": "success", "count": len(rules)}

@router.get("/rules/export")
def export_rules(
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return CategoryService.export_category_rules(db, str(current_user.tenant_id))
