from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.modules.auth import models as auth_models
from backend.app.modules.auth.dependencies import get_current_user
from backend.app.modules.finance.services.analytics_service import AnalyticsService

router = APIRouter()

@router.get("/metrics")
def get_metrics(
    account_id: str = None,
    start_date: datetime = None,
    end_date: datetime = None,
    user_id: str = None,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return AnalyticsService.get_summary_metrics(
        db, 
        str(current_user.tenant_id), 
        user_role=current_user.role,
        account_id=account_id,
        start_date=start_date,
        end_date=end_date,
        user_id=user_id
    )

@router.get("/forecast")
def get_forecast(
    days: int = 30,
    account_id: str = None,
    user_id: str = None,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return AnalyticsService.get_balance_forecast(
        db, 
        str(current_user.tenant_id), 
        days=days,
        account_id=account_id,
        user_id=user_id
    )
@router.get("/budget-history")
def get_budget_history(
    months: int = 6,
    user_id: str = None,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return AnalyticsService.get_budget_history(
        db, 
        str(current_user.tenant_id), 
        months=months,
        user_id=user_id
    )
@router.get("/net-worth-timeline")
def get_net_worth_timeline(
    days: int = 30,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return AnalyticsService.get_net_worth_timeline(
        db, 
        str(current_user.tenant_id), 
        days=days
    )

@router.get("/spending-trend")
def get_spending_trend(
    user_id: str = None,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return AnalyticsService.get_spending_trend(
        db, 
        str(current_user.tenant_id),
        user_id=user_id
    )

@router.get("/mobile-summary")
def get_mobile_summary(
    user_id: str = None,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lightweight endpoint for mobile app notifications"""
    from backend.app.modules.finance.services.mobile_service import MobileService
    return MobileService.get_mobile_summary(
        db,
        str(current_user.tenant_id),
        user_id=user_id
    )
@router.get("/heatmap")
def get_heatmap(
    start_date: datetime = None,
    end_date: datetime = None,
    user_id: str = None,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return AnalyticsService.get_heatmap_data(
        db, 
        str(current_user.tenant_id),
        start_date=start_date,
        end_date=end_date,
        user_id=user_id
    )
@router.get("/merchant-breakdown")
def get_merchant_breakdown(
    category: str = None,
    start_date: datetime = None,
    end_date: datetime = None,
    user_id: str = None,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return AnalyticsService.get_merchant_breakdown(
        db, 
        str(current_user.tenant_id),
        category=category,
        start_date=start_date,
        end_date=end_date,
        user_id=user_id
    )
