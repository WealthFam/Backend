import calendar
import uuid
import logging
import traceback
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from backend.app.core import timezone
from backend.app.core.database import get_db
from backend.app.modules.auth import models as auth_models
from backend.app.modules.auth import security, services as auth_services
from backend.app.modules.auth.dependencies import get_current_user
from backend.app.modules.finance import models as finance_models
from backend.app.modules.finance import schemas as finance_schemas
from backend.app.modules.finance.services.analytics_service import AnalyticsService
from backend.app.modules.finance.services.mutual_funds import MutualFundService
from backend.app.modules.finance.services.transaction_service import TransactionService
from backend.app.modules.ingestion import models as ingestion_models
from backend.app.modules.ingestion.services import IngestionService
from backend.app.modules.mobile import schemas as mobile_schemas
from backend.app.modules.mobile.services.expense_group_service import MobileExpenseGroupService
from backend.app.modules.mobile.services.investment_goal_service import MobileInvestmentGoalService
from backend.app.modules.ingestion.ai_service import AIService
from backend.app.modules.vault.service import VaultService as CoreVaultService
from backend.app.modules.vault import models as vault_models
from fastapi import UploadFile, File, Form
from fastapi.responses import FileResponse
import os

router = APIRouter(tags=["Mobile"])
logger = logging.getLogger(__name__)



@router.post("/login", response_model=mobile_schemas.MobileLoginResponse)
def mobile_login(
    payload: mobile_schemas.MobileLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Mobile-specific login. Authenticates user AND registers device.
    Returns a Long-Lived JWT (e.g. 30 days).
    """
    # 1. Authenticate User
    user = auth_services.AuthService.authenticate_user(db, payload.username, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 2. Register/Update Device
    device = db.query(ingestion_models.MobileDevice).filter(
        ingestion_models.MobileDevice.device_id == payload.device_id,
        ingestion_models.MobileDevice.tenant_id == str(user.tenant_id)
    ).first()
    
    if not device:
        device = ingestion_models.MobileDevice(
            tenant_id=str(user.tenant_id),
            device_id=payload.device_id,
            device_name=payload.device_name,
            is_approved=False, # Default to unapproved
            is_enabled=True,
            user_id=str(user.id)
        )
        db.add(device)
    else:
        # Update name and seen time
        device.device_name = payload.device_name
        device.last_seen_at = timezone.utcnow()
        
    db.commit()
    db.refresh(device)
    
    IngestionService.log_event(
        db, 
        str(user.tenant_id), 
        "device_login", 
        "success", 
        f"Device {payload.device_name} logged in", 
        device_id=payload.device_id
    )
    
    # Issue Long-Lived Token
    access_token_expires = timedelta(days=30) 
    access_token, jti = security.create_access_token(
        data={"sub": user.email, "tenant_id": str(user.tenant_id), "device_id": device.device_id},
        expires_delta=access_token_expires
    )
    
    # Record token in DB for revocation tracking
    db_token = auth_models.UserToken(
        user_id=user.id,
        token_jti=jti,
        expires_at=timezone.utcnow() + access_token_expires
    )
    db.add(db_token)
    db.commit()
    
    # Construct DeviceResponse dict explicitly
    device_status = {
        "id": str(device.id),
        "tenant_id": str(device.tenant_id),
        "device_id": device.device_id,
        "device_name": device.device_name,
        "is_approved": device.is_approved,
        "is_enabled": device.is_enabled,
        "is_ignored": getattr(device, 'is_ignored', False),
        "last_seen_at": device.last_seen_at or timezone.utcnow(),
        "created_at": device.created_at or timezone.utcnow(),
        "user_id": device.user_id,
        "user_name": user.full_name,
        "user_avatar": user.avatar
    }
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "expires_in": int(access_token_expires.total_seconds()),
        "device_status": device_status,
        "user_role": user.role,
        "user_name": user.full_name,
        "user_avatar": user.avatar
    }


@router.post("/register-device", response_model=mobile_schemas.DeviceResponse)
def register_device(
    payload: mobile_schemas.DeviceRegister,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually register a device if key rotation or re-install happens without full login.
    """
    device = db.query(ingestion_models.MobileDevice).filter(
        ingestion_models.MobileDevice.device_id == payload.device_id,
        ingestion_models.MobileDevice.tenant_id == str(current_user.tenant_id)
    ).first()
    
    if not device:
        device = ingestion_models.MobileDevice(
            tenant_id=str(current_user.tenant_id),
            device_id=payload.device_id,
            device_name=payload.device_name,
            fcm_token=payload.fcm_token,
            is_approved=False,
            user_id=str(current_user.id)
        )
        db.add(device)
    else:
        device.device_name = payload.device_name
        if payload.fcm_token:
            device.fcm_token = payload.fcm_token
        device.last_seen_at = timezone.utcnow()
        
    db.commit()
    db.refresh(device)
    return {"id": str(device.id), "tenant_id": str(device.tenant_id), "device_id": device.device_id, "device_name": device.device_name, "is_approved": device.is_approved, "is_enabled": device.is_enabled, "is_ignored": getattr(device, "is_ignored", False), "last_seen_at": device.last_seen_at or timezone.utcnow(), "created_at": device.created_at or timezone.utcnow(), "user_id": device.user_id, "user_name": current_user.full_name, "user_avatar": current_user.avatar}

@router.get("/status", response_model=mobile_schemas.DeviceResponse)
def check_device_status(
    device_id: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Heartbeat endpoint for mobile app to check if it's still approved.
    """
    device = db.query(ingestion_models.MobileDevice).filter(
        ingestion_models.MobileDevice.device_id == device_id,
        ingestion_models.MobileDevice.tenant_id == str(current_user.tenant_id)
    ).first()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
        
    # Enrich with user info if linked
    user_name = None
    user_avatar = None
    if device.user_id:
        user = db.query(auth_models.User).filter(auth_models.User.id == device.user_id).first()
        if user:
            user_name = user.full_name
            user_avatar = user.avatar

    return {
        "id": str(device.id),
        "tenant_id": str(device.tenant_id),
        "device_id": device.device_id,
        "device_name": device.device_name,
        "is_approved": device.is_approved,
        "is_enabled": device.is_enabled,
        "is_ignored": getattr(device, 'is_ignored', False),
        "last_seen_at": device.last_seen_at or timezone.utcnow(),
        "created_at": device.created_at or timezone.utcnow(),
        "user_id": device.user_id,
        "user_name": user_name,
        "user_avatar": user_avatar
    }

@router.post("/heartbeat", response_model=mobile_schemas.DeviceResponse)
def device_heartbeat(
    device_id: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Explicit heartbeat to update last_seen_at.
    """
    device = db.query(ingestion_models.MobileDevice).filter(
        (ingestion_models.MobileDevice.id == device_id) | (ingestion_models.MobileDevice.device_id == device_id),
        ingestion_models.MobileDevice.tenant_id == str(current_user.tenant_id)
    ).first()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
        
    device.last_seen_at = timezone.utcnow()
    db.commit()
    db.refresh(device)
    
    IngestionService.log_event(
        db, 
        str(current_user.tenant_id), 
        "heartbeat", 
        "success", 
        f"Heartbeat from {device.device_name}", 
        device_id=device.device_id
    )
    
    return {
        "id": str(device.id),
        "tenant_id": str(device.tenant_id),
        "device_id": device.device_id,
        "device_name": device.device_name,
        "is_approved": device.is_approved,
        "is_enabled": device.is_enabled,
        "is_ignored": getattr(device, 'is_ignored', False),
        "last_seen_at": device.last_seen_at or timezone.utcnow(),
        "created_at": device.created_at or timezone.utcnow(),
        "user_id": device.user_id,
        "user_name": current_user.full_name,
        "user_avatar": current_user.avatar
    }

# --- Web Dashboard Management Endpoints (also under /mobile namespace) ---

@router.get("/devices", response_model=List[mobile_schemas.DeviceResponse])
def list_devices(
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all registered devices for the tenant (for Web UI).
    """
    devices = db.query(ingestion_models.MobileDevice).filter(
        ingestion_models.MobileDevice.tenant_id == str(current_user.tenant_id)
    ).order_by(ingestion_models.MobileDevice.last_seen_at.desc()).all()
    
    enriched = []
    for d in devices:
        user_name = None
        user_avatar = None
        if d.user_id:
            user = db.query(auth_models.User).filter(auth_models.User.id == d.user_id).first()
            if user:
                user_name = user.full_name
                user_avatar = user.avatar
        enriched.append({
            "id": str(d.id),
            "tenant_id": str(d.tenant_id),
            "device_id": d.device_id,
            "device_name": d.device_name,
            "is_approved": d.is_approved,
            "is_enabled": d.is_enabled,
            "is_ignored": getattr(d, 'is_ignored', False),
            "last_seen_at": d.last_seen_at,
            "created_at": d.created_at,
            "user_id": d.user_id,
            "user_name": user_name,
            "user_avatar": user_avatar
        })
    return enriched

@router.patch("/devices/{device_id}/approve", response_model=mobile_schemas.DeviceResponse)
def approve_device(
    device_id: str,
    payload: mobile_schemas.ToggleApprovalRequest,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Toggle device approval status (Web UI only).
    """
    if current_user.role == "CHILD":
        raise HTTPException(status_code=403, detail="Only adults can manage devices")

    device = db.query(ingestion_models.MobileDevice).filter(
        ingestion_models.MobileDevice.id == device_id,
        ingestion_models.MobileDevice.tenant_id == str(current_user.tenant_id)
    ).first()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
        
    device.is_approved = payload.is_approved
    db.commit()
    db.refresh(device)
    return device

@router.delete("/devices/{device_id}")
def delete_device(
    device_id: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove/Reject a device.
    """
    device = db.query(ingestion_models.MobileDevice).filter(
        (ingestion_models.MobileDevice.id == device_id) | (ingestion_models.MobileDevice.device_id == device_id),
        ingestion_models.MobileDevice.tenant_id == str(current_user.tenant_id)
    ).first()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
        
    db.delete(device)
    db.commit()
    return {"status": "deleted"}

@router.patch("/devices/{device_id}", response_model=mobile_schemas.DeviceResponse)
def update_device(
    device_id: str,
    payload: mobile_schemas.DeviceUpdate,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update device metadata (Name, User Assignment, etc).
    """
    device = db.query(ingestion_models.MobileDevice).filter(
        (ingestion_models.MobileDevice.id == device_id) | (ingestion_models.MobileDevice.device_id == device_id),
        ingestion_models.MobileDevice.tenant_id == str(current_user.tenant_id)
    ).first()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
        
    if payload.device_name is not None:
        device.device_name = payload.device_name
    if payload.is_enabled is not None:
        device.is_enabled = payload.is_enabled
    if payload.is_ignored is not None:
        device.is_ignored = payload.is_ignored
    if payload.user_id is not None:
        device.user_id = payload.user_id
        
    db.commit()
    db.refresh(device)
    return device

@router.patch("/devices/{device_id}/enable", response_model=mobile_schemas.DeviceResponse)
def toggle_device_enabled(
    device_id: str,
    enabled: bool,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Enable or Disable ingestion for a device without removing it.
    """
    device = db.query(ingestion_models.MobileDevice).filter(
        (ingestion_models.MobileDevice.id == device_id) | (ingestion_models.MobileDevice.device_id == device_id),
        ingestion_models.MobileDevice.tenant_id == str(current_user.tenant_id)
    ).first()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
        
    device.is_enabled = enabled
    db.commit()
    db.refresh(device)
    return device

@router.patch("/devices/{device_id}/ignore", response_model=mobile_schemas.DeviceResponse)
def toggle_device_ignored(
    device_id: str,
    ignored: bool,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark a device as ignored (soft reject) or restore it.
    """
    device = db.query(ingestion_models.MobileDevice).filter(
        (ingestion_models.MobileDevice.id == device_id) | (ingestion_models.MobileDevice.device_id == device_id),
        ingestion_models.MobileDevice.tenant_id == str(current_user.tenant_id)
    ).first()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
        
    device.is_ignored = ignored
    if ignored:
        device.is_approved = False

    db.commit()
    db.refresh(device)
    return device

@router.patch("/devices/{device_id}/assign", response_model=mobile_schemas.DeviceResponse)
def assign_device_user(
    device_id: str,
    payload: mobile_schemas.AssignUserRequest,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Assign a device to a specific family member/user.
    """
    if current_user.role == "CHILD":
        raise HTTPException(status_code=403, detail="Only adults can manage devices")

    device = db.query(ingestion_models.MobileDevice).filter(
        (ingestion_models.MobileDevice.id == device_id) | (ingestion_models.MobileDevice.device_id == device_id),
        ingestion_models.MobileDevice.tenant_id == str(current_user.tenant_id)
    ).first()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
        
    device.user_id = payload.user_id
    db.commit()
    db.refresh(device)
    return device

@router.get("/members", response_model=List[mobile_schemas.MemberResponse])
def list_family_members(
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List valid family members for filtering.
    """
    if current_user.role == "CHILD":
        return [{
            "id": str(current_user.id),
            "name": current_user.full_name or current_user.email.split('@')[0],
            "role": "CHILD",
            "avatar_url": None
        }]
    
    # Return all tenant users
    users = db.query(auth_models.User).filter(
        auth_models.User.tenant_id == str(current_user.tenant_id)
    ).all()
    
    return [
        {
            "id": str(u.id),
            "name": u.full_name or u.email.split('@')[0],
            "role": u.role,
            "avatar_url": None
        }
        for u in users
    ]

def get_target_user_id(current_user, member_id):
    if current_user.role == "CHILD":
        if member_id and member_id != str(current_user.id):
             raise HTTPException(status_code=403, detail="Children can only view their own data")
        return str(current_user.id)
    return member_id

@router.get("/dashboard/summary", response_model=mobile_schemas.DashboardSummaryResponse)
def get_dashboard_summary(
    month: Optional[int] = None,
    year: Optional[int] = None,
    member_id: Optional[str] = None,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    target_user_id = get_target_user_id(current_user, member_id)
    now = timezone.utcnow()
    target_month = month or now.month
    target_year = year or now.year
    
    metrics = AnalyticsService.get_mobile_summary_metrics(
        db, str(current_user.tenant_id), user_role=current_user.role,
        month=month, year=year, user_id=target_user_id
    )
    
    # Account map for names
    account_ids = list(set(txn['account_id'] for txn in metrics["recent_transactions"]))
    accounts = db.query(finance_models.Account).filter(finance_models.Account.id.in_(account_ids)).all()
    account_map = {str(a.id): a for a in accounts}

    # Expense Group map for names
    group_ids = list(set(txn['expense_group_id'] for txn in metrics["recent_transactions"] if txn.get('expense_group_id')))
    group_map = {}
    if group_ids:
        groups = db.query(finance_models.ExpenseGroup).filter(finance_models.ExpenseGroup.id.in_(group_ids)).all()
        group_map = {str(g.id): g for g in groups}

    _, triage_count = TransactionService.get_pending_transactions(
        db, str(current_user.tenant_id), limit=1, user_id=target_user_id
    )
    family_members_count = db.query(auth_models.User).filter(auth_models.User.tenant_id == str(current_user.tenant_id)).count()
    
    pending_training_count = db.query(ingestion_models.UnparsedMessage).filter(
        ingestion_models.UnparsedMessage.tenant_id == str(current_user.tenant_id)
    ).count()

    # Document map for visual indicator
    from backend.app.modules.vault.models import DocumentVault
    linked_doc_counts = {
        row.transaction_id: row.count 
        for row in db.query(
            DocumentVault.transaction_id, 
            func.count(DocumentVault.id).label('count')
        ).filter(
            DocumentVault.tenant_id == str(current_user.tenant_id),
            DocumentVault.transaction_id.in_(list(set(txn['id'] for txn in metrics["recent_transactions"])))
        ).group_by(DocumentVault.transaction_id).all()
    }

    # Category map for icons
    category_objs = db.query(finance_models.Category).filter(
        finance_models.Category.tenant_id == str(current_user.tenant_id)
    ).all()
    cat_map = {c.name.lower(): c for c in category_objs}

    def enrich_txn(txn):
        display_category = txn.get('category') or "Uncategorized"
        ext = {
            "account_name": account_map.get(txn['account_id']).name if account_map.get(txn['account_id']) else "Unknown",
            "has_documents": linked_doc_counts.get(txn['id'], 0) > 0,
            "category_icon": resolve_category_icon(display_category, cat_map)
        }
        gid = txn.get('expense_group_id')
        if gid and group_map.get(gid):
            ext["expense_group_name"] = group_map[gid].name
        return {**txn, **ext}

    return {
        "summary": {
            "today_total": metrics.get("today_total", 0.0),
            "yesterday_total": metrics.get("yesterday_total", 0.0),
            "last_month_same_day_total": metrics.get("last_month_same_day_total", 0.0),
            "monthly_total": metrics.get("monthly_total", 0.0),
            "monthly_investment": metrics.get("monthly_investment", 0.0),
            "monthly_income": metrics.get("monthly_income", 0.0),
            "currency": metrics.get("currency", "INR"),
            "daily_budget_limit": metrics.get("daily_budget_limit", 0.0),
            "prorated_budget": metrics.get("prorated_budget", 0.0)
        },
        "budget": metrics.get("budget_health", {"limit": 0, "spent": 0, "percentage": 0}),
        "recent_transactions": [
            enrich_txn(txn) for txn in metrics["recent_transactions"]
        ],
        "pending_triage_count": triage_count,
        "pending_training_count": pending_training_count,
        "family_members_count": family_members_count
    }

@router.get("/dashboard/trends", response_model=mobile_schemas.DashboardTrendsResponse)
def get_dashboard_trends(
    month: Optional[int] = None,
    year: Optional[int] = None,
    member_id: Optional[str] = None,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    target_user_id = get_target_user_id(current_user, member_id)
    now = timezone.utcnow()
    target_month = month or now.month
    target_year = year or now.year
    
    return AnalyticsService.get_mobile_dashboard_trends(
        db, str(current_user.tenant_id), target_year, target_month, user_id=target_user_id
    )

@router.get("/dashboard/categories", response_model=mobile_schemas.DashboardCategoriesResponse)
def get_dashboard_categories(
    month: Optional[int] = None,
    year: Optional[int] = None,
    member_id: Optional[str] = None,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    target_user_id = get_target_user_id(current_user, member_id)
    now = timezone.utcnow()
    target_month = month or now.month
    target_year = year or now.year
    return AnalyticsService.get_mobile_dashboard_categories(
        db, str(current_user.tenant_id), target_month, target_year, user_id=target_user_id
    )

@router.get("/vendor/stats")
def get_vendor_stats(
    vendor_name: str,
    skip: int = 0,
    limit: int = 3,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get spending trends and recent transactions for a specific merchant.
    """
    return TransactionService.get_vendor_stats(
        db, 
        str(current_user.tenant_id), 
        vendor_name, 
        user_id=None, # TBD: Add support for filtering by family member if needed
        skip=skip, 
        limit=limit
    )

@router.get("/dashboard/investments", response_model=mobile_schemas.DashboardInvestmentsResponse)
def get_dashboard_investments(
    member_id: Optional[str] = None,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role == "CHILD":
        return {"investment_summary": None}
    
    target_user_id = get_target_user_id(current_user, member_id)
    inv_data = MutualFundService.get_portfolio_analytics(db, str(current_user.tenant_id), user_id=target_user_id)
    
    if inv_data["current_value"] <= 0 and inv_data["total_invested"] <= 0:
        return {"investment_summary": None}


    return {
        "investment_summary": {
            "total_invested": inv_data["total_invested"],
            "current_value": inv_data["current_value"],
            "profit_loss": inv_data.get("profit_loss", inv_data["current_value"] - inv_data["total_invested"]),
            "xirr": inv_data["xirr"],
            "sparkline": inv_data.get("sparkline", []),
            "day_change": inv_data.get("day_change", 0.0),
            "day_change_percent": inv_data.get("day_change_percent", 0.0)
        }
    }

@router.get("/dashboard", response_model=mobile_schemas.MobileDashboardResponse)
def get_mobile_dashboard(
    month: Optional[int] = None,
    year: Optional[int] = None,
    member_id: Optional[str] = None,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Deprecated: Use granular endpoints. Aggregates all for legacy support.
    """
    dashboard = AnalyticsService.get_consolidated_dashboard(
        db, str(current_user.tenant_id), current_user, 
        month=month, year=year, user_id=get_target_user_id(current_user, member_id)
    )
    return dashboard

@router.get("/heatmap")
def get_mobile_heatmap(
    month: Optional[int] = None,
    year: Optional[int] = None,
    member_id: Optional[str] = None,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    target_user_id = get_target_user_id(current_user, member_id)
    now = timezone.utcnow()
    target_month = month or now.month
    target_year = year or now.year
    
    start_date = timezone.ensure_utc(datetime(target_year, target_month, 1))
    last_day = calendar.monthrange(target_year, target_month)[1]
    end_date = timezone.ensure_utc(datetime(target_year, target_month, last_day, 23, 59, 59))

    return AnalyticsService.get_heatmap_data(
        db, str(current_user.tenant_id), 
        start_date=start_date, end_date=end_date, 
        user_id=target_user_id
    )

@router.get("/ingestion/triage", response_model=List[mobile_schemas.RecentTransaction])
def list_mobile_triage(
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all pending transactions for the mobile app to review.
    """
    items, total = TransactionService.get_pending_transactions(
        db, str(current_user.tenant_id), limit=100, sort_order="desc"
    )
    # Ensure owners are joined for faster access (already joined loaded in get_pending_transactions but just joinedload)
    # Wait, get_pending_transactions has options(joinedload(PendingTransaction.account)).
    # Let's ensure owners are pre-loaded to avoid N+1.
    # We can perform a bulk lookup for owners.
    owner_ids = list(set(txn.account.owner_id for txn in items if txn.account and txn.account.owner_id))
    owners_map = {str(u.id): u.full_name or u.email.split('@')[0] for u in db.query(auth_models.User).filter(auth_models.User.id.in_(owner_ids)).all()}
    
    enriched = []
    for txn in items:
        owner_name = owners_map.get(str(txn.account.owner_id), "Unknown") if txn.account and txn.account.owner_id else "Unknown"

        enriched.append({
            "id": txn.id,
            "date": txn.date,
            "description": txn.description or "Review Required",
            "amount": float(txn.amount),
            "category": txn.category,
            "account_name": txn.account.name if txn.account else "Unknown",
            "account_owner_name": owner_name,
            "source": txn.source,
            "recipient": txn.recipient or txn.description,
            "has_documents": db.query(vault_models.DocumentVault).filter(vault_models.DocumentVault.transaction_id == txn.id).count() > 0
        })
    return enriched

@router.post("/ingestion/triage/{triage_id}/approve")
def approve_mobile_triage(
    triage_id: str,
    payload: dict,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Approve a transaction from triage via mobile app.
    """
    return TransactionService.process_triage(
        db, str(current_user.tenant_id), triage_id, approve=True, data=payload
    )

@router.delete("/ingestion/triage/{triage_id}")
def discard_mobile_triage(
    triage_id: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Discard a transaction from triage via mobile app.
    """
    return TransactionService.process_triage(
        db, str(current_user.tenant_id), triage_id, approve=False
    )


def resolve_category_icon(display_category: str, cat_map: Dict[str, finance_models.Category]) -> Optional[str]:
    """
    Common logic to resolve an icon for a category, with hardcoded fallbacks for 
    high-frequency categories if DB icon is missing. Matches web app behavior.
    """
    if not display_category:
        return "🏷️"
        
    leaf_cat_name = display_category.split(" › ")[-1].lower()
    
    # 1. Try DB map
    if leaf_cat_name in cat_map:
        db_icon = cat_map[leaf_cat_name].icon
        if db_icon:
            return db_icon
            
    # 2. Fallback to hardcoded common icons
    DEFAULT_ICONS = {
        "food": "🍔", "groceries": "🛒", "rent": "🏠", "shopping": "🛍️",
        "transport": "🚗", "travel": "✈️", "health": "💊", "entertainment": "🎬",
        "utilities": "💡", "salary": "💰", "transfer": "↔️", "investment": "📈",
        "education": "🎓", "gift": "🎁", "other": "📦", "uncategorized": "📁"
    }
    # Check if leaf name matches any key (substring match for broader hits)
    for key, emoji in DEFAULT_ICONS.items():
        if key in leaf_cat_name:
            return emoji
            
    return "🏷️"


@router.get("/transactions", response_model=mobile_schemas.TransactionResponse)
def list_mobile_transactions(
    page: int = 1,
    page_size: int = 20,
    month: Optional[int] = None,
    year: Optional[int] = None,
    day: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    member_id: Optional[str] = None,
    expense_group_id: Optional[str] = None,
    category: Optional[str] = None,
    account_id: Optional[str] = None,
    search: Optional[str] = None,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Paginated transactions list for infinite scroll.
    """
    # Authorization logic for member_id
    target_user_id = None # Default to None (All) for Adults
    
    if current_user.role == "CHILD":
        # Child can only see their own data
        target_user_id = str(current_user.id)
        if member_id and member_id != target_user_id:
            raise HTTPException(status_code=403, detail="Children can only view their own data")
    elif member_id:
        # Adults can view specific member
        target_user_id = member_id
        
    query = db.query(finance_models.Transaction).options(
        joinedload(finance_models.Transaction.account).joinedload(finance_models.Account.owner)
    ).filter(
        finance_models.Transaction.tenant_id == str(current_user.tenant_id),
        finance_models.Transaction.is_transfer == False,
        finance_models.Transaction.exclude_from_reports == False
    )

    # Fetch categories for enrichment
    from backend.app.modules.finance.models import Category
    category_objs = db.query(Category).filter(Category.tenant_id == str(current_user.tenant_id)).all()
    cat_map = {c.name.lower(): c for c in category_objs}
    cat_id_map = {c.id: c for c in category_objs}
    
    # Filter by user ownership if target_user_id is set
    if target_user_id:
        query = query.join(
            finance_models.Account, finance_models.Transaction.account_id == finance_models.Account.id
        ).filter(
            or_(finance_models.Account.owner_id == target_user_id, finance_models.Account.owner_id == None)
        )

    if expense_group_id:
        query = query.filter(finance_models.Transaction.expense_group_id == expense_group_id)

    if category:
        # Match either exact name or as the leaf of a hierarchical category
        query = query.filter(
            or_(
                finance_models.Transaction.category == category,
                finance_models.Transaction.category.like(f"% › {category}")
            )
        )
    
    if account_id:
        query = query.filter(finance_models.Transaction.account_id == account_id)
    
    if search:
        query = query.filter(finance_models.Transaction.description.ilike(f"%{search}%"))
    
    if month and year:
        if day:
            s_date = datetime(year, month, day)
            e_date = datetime(year, month, day, 23, 59, 59)
        else:
            s_date = datetime(year, month, 1)
            last_day = calendar.monthrange(year, month)[1]
            e_date = datetime(year, month, last_day, 23, 59, 59)
        query = query.filter(finance_models.Transaction.date >= s_date, finance_models.Transaction.date <= e_date)
    elif start_date:
        try:
            s_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.filter(finance_models.Transaction.date >= s_date)
            if end_date:
                e_date = datetime.fromisoformat(end_date.replace('Z', '+00:00')).replace(hour=23, minute=59, second=59)
                query = query.filter(finance_models.Transaction.date <= e_date)
        except Exception as e:
            logger.error(f"Error parsing dates: {e}")
        
    total_count = query.count()
    
    transactions = query.order_by(finance_models.Transaction.date.desc()) \
                        .offset((page - 1) * page_size) \
                        .limit(page_size) \
                        .all()
                        
    # Document link detection
    from backend.app.modules.vault.models import DocumentVault
    txn_ids = [txn.id for txn in transactions]
    linked_doc_counts = {
        row.transaction_id: row.count 
        for row in db.query(
            DocumentVault.transaction_id, 
            func.count(DocumentVault.id).label('count')
        ).filter(
            DocumentVault.tenant_id == str(current_user.tenant_id),
            DocumentVault.transaction_id.in_(txn_ids)
        ).group_by(DocumentVault.transaction_id).all()
    }

    # Enrich with owner info (simplified) or mapped
    enriched = []
    for txn in transactions:
        # Use relationship for owner info (pre-loaded via joinedload)
        owner_name = txn.account.owner.full_name or txn.account.owner.email.split('@')[0] if txn.account and txn.account.owner else "Unknown"
        
        # Category enrichment
        display_category = txn.category
        if not display_category or display_category == "Uncategorized":
            # Optional: try to find if it has an expense group or other hint
            display_category = "Uncategorized"
        
        # Ensure hierarchy display parity with web
        if display_category and " › " not in display_category:
            cat_obj = cat_map.get(display_category.lower())
            if cat_obj and cat_obj.parent_id:
                parent = cat_id_map.get(cat_obj.parent_id)
                if parent:
                    display_category = f"{parent.name} › {cat_obj.name}"

        # Determine category icon
        cat_icon = resolve_category_icon(display_category, cat_map)

        enriched.append({
            "id": txn.id,
            "date": txn.date,
            "description": txn.description,
            "recipient": txn.recipient or txn.description,
            "amount": float(txn.amount),
            "category": display_category,
            "category_icon": cat_icon,
            "account_id": str(txn.account_id),
            "account_name": txn.account.name if txn.account else "Unknown",
            "account_owner_name": owner_name,
            "expense_group_id": txn.expense_group_id,
            "source": txn.source,
            "is_transfer": txn.is_transfer,
            "exclude_from_reports": txn.exclude_from_reports,
            "has_documents": linked_doc_counts.get(txn.id, 0) > 0
        })
        
    has_next = (page * page_size) < total_count
    
    return {
        "data": enriched,
        "next_page": page + 1 if has_next else None
    }
    
class CreateTransactionRequest(BaseModel):
    account_id: str
    amount: float
    description: str
    category: str
    date: str

@router.post("/transactions", response_model=mobile_schemas.RecentTransaction)
def create_mobile_transaction(
    payload: CreateTransactionRequest,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new transaction (manual entry).
    """
    from datetime import datetime
    
    # Verify account ownership
    account = db.query(finance_models.Account).filter(
         finance_models.Account.id == payload.account_id,
         or_(finance_models.Account.owner_id == str(current_user.id), finance_models.Account.owner_id == None),
         finance_models.Account.tenant_id == str(current_user.tenant_id)
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found or access denied")
        
    txn = finance_models.Transaction(
        id=str(uuid.uuid4()),
        tenant_id=str(current_user.tenant_id),
        account_id=payload.account_id,
        amount=payload.amount,
        description=payload.description,
        category=payload.category,
        date=datetime.fromisoformat(payload.date),
        is_transfer=False # Simple manual entry usually not transfer
    )
    
    db.add(txn)
    db.commit()
    db.refresh(txn)
    
    return {
        "id": txn.id,
        "date": txn.date,
        "description": txn.description,
        "amount": float(txn.amount),
        "category": txn.category
    }

@router.get("/funds", response_model=mobile_schemas.MobileFundsResponse)
def get_mobile_funds(
    member_id: Optional[str] = None,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get Mutual Funds summary and holdings.
    RESTRICTED: Child accounts cannot access this endpoint.
    """
    if current_user.role == "CHILD":
        raise HTTPException(status_code=403, detail="Mutual funds are restricted for children")
        
    target_user_id = member_id if member_id else None
    
    from backend.app.modules.finance.services.mutual_funds import MutualFundService
    
    # 1. Fetch Analytics for Summary (Ensures parity with Web)
    analytics = MutualFundService.get_portfolio_analytics(db, str(current_user.tenant_id), user_id=target_user_id)
    
    # 2. Fetch Detailed Holdings
    holdings = MutualFundService.get_portfolio(db, str(current_user.tenant_id), target_user_id)
    
    # 3. Combine Folios
    combined_holdings = {}
    
    for h in holdings:
        scheme_code = h['scheme_code']
        units = float(h.get('units', 0))
        cur = float(h.get('current_value', 0))
        inv = float(h.get('invested_value', 0))
        
        if scheme_code not in combined_holdings:
            combined_holdings[scheme_code] = {
                "scheme_code": scheme_code,
                "scheme_name": h['scheme_name'],
                "total_units": 0.0,
                "current_value": 0.0,
                "invested_value": 0.0,
                "category": h.get('category'),
                "last_updated": h.get('last_updated_at', ''),
                "folios": []
            }
        
        ch = combined_holdings[scheme_code]
        ch["total_units"] += units
        ch["current_value"] += cur
        ch["invested_value"] += inv
        ch["folios"].append(mobile_schemas.Folio(
            folio_number=h.get('folio_number', 'Unknown'),
            units=units,
            current_value=cur,
            invested_value=inv,
            profit_loss=cur - inv
        ))
    
    clean_holdings = []
    from backend.app.modules.finance.services.external.nav_service import NAVService
    for s_code, ch in combined_holdings.items():
        cur = ch["current_value"]
        inv = ch["invested_value"]
        total_units = ch["total_units"]
        
        # Calculate day change for combined holding
        day_change = 0.0
        try:
            delta_info = NAVService.get_latest_nav_delta(s_code)
            day_change = float(total_units) * float(delta_info.get("delta", 0))
        except:
            pass

        clean_holdings.append(mobile_schemas.FundHolding(
            scheme_code=s_code,
            scheme_name=ch["scheme_name"],
            units=total_units,
            current_value=cur,
            invested_value=inv,
            profit_loss=cur - inv,
            last_updated=ch["last_updated"],
            category=ch["category"],
            day_change=day_change,
            day_change_percentage=(day_change / (cur - day_change) * 100) if (cur - day_change) > 0 else 0.0,
            folios=ch["folios"]
        ))

    # Calculate Top Gainers/Losers for insights (on combined holdings)
    # Sort by profit/loss percentage
    def get_pl_percent(h):
        inv = h.invested_value
        if inv > 0:
            return float(h.profit_loss / inv) * 100
        return 0.0

    sorted_holdings = sorted(clean_holdings, key=get_pl_percent, reverse=True)
    top_gainers = sorted_holdings[:3]
    top_losers = sorted_holdings[-3:] if len(sorted_holdings) > 3 else []
    top_losers = [h for h in top_losers if get_pl_percent(h) < 0] # Only show if actually losing

    # Generate dynamic text insights
    text_insights = []
    asset_alloc = analytics.get("asset_allocation")
    
    # 1. Diversification insight
    if asset_alloc:
        active_assets = [k for k, v in asset_alloc.items() if v > 0]
        if len(active_assets) >= 3:
            text_insights.append(f"Your portfolio is well diversified across {len(active_assets)} asset classes.")
        elif "equity" in active_assets and asset_alloc["equity"] > 80:
            text_insights.append("Your portfolio is highly concentrated in Equity (High Risk/High Reward).")
            
    # 2. Concentration insight
    if len(clean_holdings) > 3:
        total_val = float(analytics.get("current_value", 0))
        if total_val > 0:
            top_3_val = sum(h.current_value for h in sorted_holdings[:3])
            concentration = (float(top_3_val) / total_val) * 100
            if concentration > 70:
                text_insights.append(f"Top 3 holdings account for {concentration:.1f}% of your portfolio.")

    # 3. Best performer insight
    if top_gainers:
        best = top_gainers[0]
        best_pl = get_pl_percent(best)
        if best_pl > 15:
            text_insights.append(f"{best.scheme_name} is your star performer with {best_pl:.1f}% returns.")

    return {
        "total_invested": analytics.get("total_invested", 0.0),
        "total_current": analytics.get("current_value", 0.0),
        "total_pl": analytics.get("profit_loss", 0.0),
        "day_change": analytics.get("day_change", 0.0),
        "day_change_percentage": analytics.get("day_change_percent", 0.0),
        "xirr": analytics.get("xirr"),
        "asset_allocation": asset_alloc,
        "top_gainers": top_gainers,
        "top_losers": top_losers,
        "text_insights": text_insights,
        "holdings": clean_holdings
    }

@router.get("/funds/{scheme_code}", response_model=mobile_schemas.FundDetailResponse)
def get_fund_details(
    scheme_code: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed information for a specific mutual fund scheme.
    """
    tenant_id = str(current_user.tenant_id)
    from backend.app.modules.finance.services.mutual_funds import MutualFundService
    from backend.app.modules.finance.models import MutualFundHolding, MutualFundsMeta, MutualFundOrder
    from backend.app.modules.finance.services.external.nav_service import NAVService
    from datetime import date, timedelta
    
    # 1. Fetch Holdings for this scheme
    holdings = db.query(MutualFundHolding).filter(
        MutualFundHolding.tenant_id == tenant_id,
        MutualFundHolding.scheme_code == scheme_code,
        MutualFundHolding.is_deleted == False
    ).all()
    
    if not holdings:
        raise HTTPException(status_code=404, detail="No holdings found for this scheme")
    
    # 2. Aggregates
    total_units = sum(float(h.units) for h in holdings)
    total_current = sum(float(h.current_value or 0) for h in holdings)
    total_invested = sum(float(h.invested_value or 0) for h in holdings)
    
    folios = [
        mobile_schemas.Folio(
            folio_number=h.folio_number or "Unknown",
            units=float(h.units),
            current_value=float(h.current_value or 0),
            invested_value=float(h.invested_value or 0),
            profit_loss=float(h.current_value or 0) - float(h.invested_value or 0)
        ) for h in holdings
    ]
    
    # 3. Meta
    meta = db.query(MutualFundsMeta).filter(MutualFundsMeta.scheme_code == scheme_code).first()
    
    # 4. Timeline & Benchmark
    # First purchase date
    first_order = db.query(MutualFundOrder).filter(
        MutualFundOrder.tenant_id == tenant_id,
        MutualFundOrder.scheme_code == scheme_code,
        MutualFundOrder.is_deleted == False
    ).order_by(MutualFundOrder.order_date.asc()).first()
    
    start_date = (first_order.order_date.date() - timedelta(days=10)) if first_order else (date.today() - timedelta(days=365))
    end_date = date.today()
    
    history = NAVService.get_nav_history(scheme_code, start_date, end_date)
    
    # Benchmark (Nifty 50 = 120716)
    benchmark_history = NAVService.get_nav_history("120716", start_date, end_date)
    bm_map = {entry['date']: float(entry['value']) for entry in benchmark_history}
    
    timeline = [
        mobile_schemas.TimelinePoint(
            date=entry['date'],
            value=float(entry['value']),
            benchmark_value=bm_map.get(entry['date'])
        ) for entry in history
    ]
    
    # 5. Events
    orders = db.query(MutualFundOrder).filter(
        MutualFundOrder.tenant_id == tenant_id,
        MutualFundOrder.scheme_code == scheme_code,
        MutualFundOrder.is_deleted == False
    ).order_by(MutualFundOrder.order_date.desc()).all()
    
    events = [
        mobile_schemas.InvestmentEvent(
            date=o.order_date.strftime("%Y-%m-%d"),
            amount=float(o.amount),
            type=o.type,
            units=float(o.units)
        ) for o in orders
    ]
    
    # 6. Day Change
    day_change = 0.0
    try:
        delta_info = NAVService.get_latest_nav_delta(scheme_code)
        day_change = float(total_units) * float(delta_info.get("delta", 0))
    except:
        pass

    return mobile_schemas.FundDetailResponse(
        scheme_code=scheme_code,
        scheme_name=meta.scheme_name if meta else holdings[0].scheme_name,
        category=meta.category if meta else "Other",
        fund_house=meta.fund_house if meta else None,
        total_units=total_units,
        current_value=total_current,
        invested_value=total_invested,
        profit_loss=total_current - total_invested,
        profit_loss_percentage=(total_current - total_invested) / total_invested * 100 if total_invested > 0 else 0,
        day_change=day_change,
        day_change_percentage=(day_change / (total_current - day_change) * 100) if (total_current - day_change) > 0 else 0.0,
        xirr=None, 
        folios=folios,
        timeline=timeline,
        events=events
    )

@router.get("/categories", response_model=List[mobile_schemas.Category])
def get_categories(
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from backend.app.modules.finance.services.category_service import CategoryService
    return CategoryService.get_categories(db, str(current_user.tenant_id), tree=True)

@router.patch("/transactions/{transaction_id}", response_model=mobile_schemas.RecentTransaction)
def update_transaction_category(
    transaction_id: str,
    payload: mobile_schemas.UpdateTransactionCategoryRequest,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from backend.app.modules.finance.services.category_service import CategoryService
    from backend.app.modules.finance import schemas as finance_schemas
    
    # 1. Update Transaction
    txn = db.query(finance_models.Transaction).filter(
        finance_models.Transaction.id == transaction_id,
        finance_models.Transaction.tenant_id == str(current_user.tenant_id)
    ).first()
    
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
        
    txn.category = payload.category
    db.commit()
    
    # 2. Create Rule if requested
    if payload.create_rule and payload.rule_keywords:
        rule_in = finance_schemas.CategoryRuleCreate(
            name=f"Auto {payload.category} for {payload.rule_keywords[0]}",
            category=payload.category,
            keywords=payload.rule_keywords,
            priority=10
        )
        CategoryService.create_category_rule(db, rule_in, str(current_user.tenant_id))
        
    db.refresh(txn)
    
    return {
        "id": txn.id,
        "date": txn.date,
        "description": txn.description,
        "amount": float(txn.amount),
        "category": txn.category
    }

from backend.app.modules.notifications.schemas import AlertSchema

@router.get("/alerts", response_model=List[AlertSchema])
def get_pulse_alerts(
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Fetch unread/pending alerts for the mobile app.
    Real-time push alternative for foreground polling.
    """
    from backend.app.modules.notifications.models import Alert
    from sqlalchemy import or_

    # Get alerts for this user or all family
    alerts = db.query(Alert).filter(
        Alert.tenant_id == str(current_user.tenant_id),
        or_(Alert.user_id == str(current_user.id), Alert.user_id == None),
        Alert.is_read == False
    ).order_by(Alert.created_at.desc()).limit(10).all()

    # Mark as read after delivery (polling logic)
    for alert in alerts:
        alert.is_read = True
    
    db.commit()
    return alerts

@router.post("/devices/{device_id}/test-notification")
def test_device_notification(
    device_id: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Trigger a test notification for a specific device (via Alert system).
    """
    device = db.query(ingestion_models.MobileDevice).filter(
        (ingestion_models.MobileDevice.id == device_id) | (ingestion_models.MobileDevice.device_id == device_id),
        ingestion_models.MobileDevice.tenant_id == str(current_user.tenant_id)
    ).first()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
        
    from backend.app.modules.notifications import NotificationService
    
    NotificationService.create_alert(
        db, 
        str(current_user.tenant_id),
        title="🧪 Test Notification",
        body=f"Sent to {device.device_name} at {timezone.utcnow().strftime('%H:%M:%S')}",
        user_id=device.user_id,
        category="INFO"
    )
    
    return {"status": "sent", "message": "Test alert created"}

@router.get("/expense-groups", response_model=List[finance_schemas.ExpenseGroupRead])
def get_mobile_expense_groups(
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if user is child (filtered view)
    user_id = str(current_user.id) if current_user.role == "CHILD" else None
    return MobileExpenseGroupService.get_expense_groups(db, str(current_user.tenant_id), user_id=user_id)

@router.post("/expense-groups", response_model=finance_schemas.ExpenseGroupRead)
def create_mobile_expense_group(
    group: finance_schemas.ExpenseGroupCreate,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return MobileExpenseGroupService.create_expense_group(db, group, str(current_user.tenant_id))

@router.get("/expense-groups/{group_id}", response_model=finance_schemas.ExpenseGroupRead)
def get_mobile_expense_group(
    group_id: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if user is child (filtered view)
    user_id = str(current_user.id) if current_user.role == "CHILD" else None
    
    group = MobileExpenseGroupService.get_expense_group(db, group_id, str(current_user.tenant_id), user_id=user_id)
    if not group:
        raise HTTPException(status_code=404, detail="Expense group not found")
    return group

@router.put("/expense-groups/{group_id}", response_model=finance_schemas.ExpenseGroupRead)
def update_mobile_expense_group(
    group_id: str,
    update: finance_schemas.ExpenseGroupUpdate,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    group = MobileExpenseGroupService.update_expense_group(db, group_id, update, str(current_user.tenant_id))
    if not group:
        raise HTTPException(status_code=404, detail="Expense group not found")
    return group

@router.delete("/expense-groups/{group_id}")
def delete_mobile_expense_group(
    group_id: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not MobileExpenseGroupService.delete_expense_group(db, group_id, str(current_user.tenant_id)):
        raise HTTPException(status_code=404, detail="Expense group not found")
    return {"status": "success"}

@router.post("/expense-groups/{group_id}/link")
def mobile_link_transactions(
    group_id: str,
    payload: finance_schemas.BulkLinkTransactionsRequest,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    count = MobileExpenseGroupService.link_transactions(
        db, group_id, payload.transaction_ids, str(current_user.tenant_id)
    )
    return {"status": "success", "linked_count": count}

@router.post("/expense-groups/{group_id}/unlink")
def mobile_unlink_transactions(
    group_id: str,
    payload: finance_schemas.BulkLinkTransactionsRequest,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    count = MobileExpenseGroupService.unlink_transactions(
        db, group_id, payload.transaction_ids, str(current_user.tenant_id)
    )
    return {"status": "success", "unlinked_count": count}

@router.get("/mobile-summary")
def get_mobile_summary(
    user_id: Optional[str] = None,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Standardized lightweight endpoint for mobile background tasks/notifications"""
    return AnalyticsService.get_mobile_summary_lightweight(
        db,
        str(current_user.tenant_id),
        user_id=user_id
    )

# --- Spending Heatmap ---

@router.get("/heatmap")
def get_mobile_heatmap(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    member_id: Optional[str] = None,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    target_user_id = get_target_user_id(current_user, member_id)
    s_date = datetime.fromisoformat(start_date) if start_date and start_date.strip() else None
    e_date = datetime.fromisoformat(end_date) if end_date and end_date.strip() else None
    return AnalyticsService.get_heatmap_data(
        db, str(current_user.tenant_id),
        start_date=s_date, end_date=e_date, user_id=target_user_id
    )

@router.get("/ingestion/triage/{pending_id}/matches")
def get_triage_matches(
    pending_id: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    pending = db.query(ingestion_models.PendingTransaction).filter(
        ingestion_models.PendingTransaction.id == pending_id,
        ingestion_models.PendingTransaction.tenant_id == str(current_user.tenant_id)
    ).first()
    if not pending: return []
    
    matches = TransactionService.get_potential_transfer_matches(
        db, str(current_user.tenant_id), 
        float(pending.amount), pending.date, str(pending.account_id)
    )
    return [
        {
            "id": m.id,
            "date": m.date,
            "description": m.description,
            "amount": float(m.amount),
            "account_name": m.account.name if m.account else "Unknown",
            "category": m.category
        } for m in matches
    ]

@router.get("/ingestion/matches")
def get_general_matches(
    amount: float,
    date: str,
    account_id: str,
    target_account_id: Optional[str] = None,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    dt = datetime.fromisoformat(date.replace('Z', '+00:00'))
    matches = TransactionService.get_potential_transfer_matches(
        db, str(current_user.tenant_id), amount, dt, account_id
    )
    return [
        {
            "id": m.id,
            "date": m.date,
            "description": m.description,
            "amount": float(m.amount),
            "account_name": m.account.name if m.account else "Unknown",
            "category": m.category
        } for m in matches
    ]

# --- Investment Goals ---

@router.get("/investment-goals", response_model=List[finance_schemas.InvestmentGoalProgress])
def get_mobile_investment_goals(
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_id = str(current_user.id) if current_user.role == "CHILD" else None
    return MobileInvestmentGoalService.get_goals(db, str(current_user.tenant_id), user_id=user_id)

@router.post("/investment-goals", response_model=finance_schemas.InvestmentGoalRead)
def create_mobile_investment_goal(
    goal: finance_schemas.InvestmentGoalCreate,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return MobileInvestmentGoalService.create_goal(db, goal, str(current_user.tenant_id))

@router.get("/investment-goals/{goal_id}", response_model=finance_schemas.InvestmentGoalProgress)
def get_mobile_investment_goal(
    goal_id: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_id = str(current_user.id) if current_user.role == "CHILD" else None
    goal = MobileInvestmentGoalService.get_goal(db, goal_id, str(current_user.tenant_id), user_id=user_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Investment goal not found")
    return goal

@router.put("/investment-goals/{goal_id}", response_model=finance_schemas.InvestmentGoalRead)
def update_mobile_investment_goal(
    goal_id: str,
    update: finance_schemas.InvestmentGoalUpdate,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    goal = MobileInvestmentGoalService.update_goal(db, goal_id, update, str(current_user.tenant_id))
    if not goal:
        raise HTTPException(status_code=404, detail="Investment goal not found")
    return goal

@router.delete("/investment-goals/{goal_id}")
def delete_mobile_investment_goal(
    goal_id: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    success = MobileInvestmentGoalService.delete_goal(db, goal_id, str(current_user.tenant_id))
    if not success:
        raise HTTPException(status_code=404, detail="Investment goal not found")
    return {"status": "success"}

@router.post("/investment-goals/{goal_id}/link")
def link_holding_to_goal(
    goal_id: str,
    payload: Dict, # {"holding_id": "..."}
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    holding_id = payload.get("holding_id")
    if not holding_id:
         raise HTTPException(status_code=400, detail="holding_id is required")
    success = MobileInvestmentGoalService.link_holding(db, goal_id, holding_id, str(current_user.tenant_id))
    return {"status": "success" if success else "failed"}

@router.post("/investment-goals/unlink")
def unlink_holding_from_goal(
    payload: Dict, # {"holding_id": "..."}
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    holding_id = payload.get("holding_id")
    if not holding_id:
         raise HTTPException(status_code=400, detail="holding_id is required")
    success = MobileInvestmentGoalService.unlink_holding(db, holding_id, str(current_user.tenant_id))
    return {"status": "success" if success else "failed"}

@router.get("/accounts")
def list_mobile_accounts(
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List accounts for mobile precision annotation.
    """
    from backend.app.modules.finance.services.account_service import AccountService
    accounts = AccountService.get_accounts(db, str(current_user.tenant_id), user_role=current_user.role)
    return {"data": accounts}

class ForensicExtractionRequest(BaseModel):
    content: str

@router.get("/ai/forensic-parse")
@router.post("/ai/forensic-parse")
def forensic_parse_transaction(
    payload: Optional[ForensicExtractionRequest] = None,
    content: Optional[str] = Query(None),
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Forensic AI extraction: Deep-parses a raw transaction string using advanced logic.
    Used for triage and strategic debugging of ingestion failures.
    """
    actual_content = content
    if payload:
        actual_content = payload.content

    if not actual_content:
        raise HTTPException(status_code=400, detail="Content is required")

    try:
        result = AIService.auto_parse_transaction(db, str(current_user.tenant_id), actual_content)
        if not result:
            return {"amount": 0.0, "description": "AI Extraction Failed", "category": "Uncategorized", "type": "DEBIT"}
        
        return {
            "amount": result.get("amount", 0.0),
            "description": result.get("recipient", result.get("description", "Unknown")),
            "category": result.get("category", "Uncategorized"),
            "type": result.get("type", "DEBIT"),
            "date": result.get("date"),
            "account_mask": result.get("account_mask")
        }
    except Exception as e:
        detail = str(e).upper()
        status_code = 500
        
        if "RESOURCE_EXHAUSTED" in detail or "429" in detail:
            status_code = 429
            error_detail = "AI quota exceeded. Please try again in a few seconds."
            logger.warning(f"AI Quota Exceeded for user {current_user.id}")
        else:
            error_detail = str(e)
            logger.error(f"AI Forensic Parse Error: {e}")
            logger.error(traceback.format_exc())
            
        raise HTTPException(status_code=status_code, detail=error_detail)

@router.get("/heatmap/calendar")
def get_mobile_calendar_heatmap(
    days: int = 365,
    month: Optional[int] = None,
    year: Optional[int] = None,
    member_id: Optional[str] = None,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get daily spending totals for the last 'days' days for calendar heatmap.
    Supports filtering by month/year to show pulse for a specific period.
    """
    target_user_id = get_target_user_id(current_user, member_id)
    
    end_date = None
    if year and month:
        # Last day of selected month/year
        import calendar
        _, last_day = calendar.monthrange(year, month)
        end_date = datetime(year, month, last_day, 23, 59, 59)
    elif year:
        # End of selected year
        end_date = datetime(year, 12, 31, 23, 59, 59)

    return AnalyticsService.get_daily_spending_history(
        db, str(current_user.tenant_id), 
        days=days, 
        user_id=target_user_id,
        end_date=end_date
    )

# --- Vault Proxies ---

@router.get("/vault")
def list_mobile_vault(
    transaction_id: Optional[str] = None,
    parent_id: Optional[str] = "ROOT",
    search: Optional[str] = None,
    is_folder: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    items, total = CoreVaultService.get_documents(
        db=db,
        tenant_id=str(current_user.tenant_id),
        user_id=str(current_user.id),
        transaction_id=transaction_id,
        parent_id=parent_id,
        search=search,
        is_folder=is_folder,
        skip=skip,
        limit=limit,
        role=current_user.role
    )
    return {"data": items, "total": total}

@router.post("/vault/upload")
async def upload_mobile_vault_document(
    file: UploadFile = File(...),
    file_type: vault_models.DocumentType = Form(vault_models.DocumentType.OTHER),
    transaction_id: Optional[str] = Form(None),
    parent_id: Optional[str] = Form(None),
    is_shared: bool = Form(True),
    description: Optional[str] = Form(None),
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return await CoreVaultService.upload_document(
        db=db,
        tenant_id=str(current_user.tenant_id),
        owner_id=str(current_user.id),
        file=file,
        file_type=file_type,
        transaction_id=transaction_id,
        parent_id=parent_id,
        is_shared=is_shared,
        description=description
    )

@router.post("/vault/folders")
def create_mobile_vault_folder(
    name: str = Form(...),
    parent_id: Optional[str] = Form(None),
    is_shared: bool = Form(True),
    description: Optional[str] = Form(None),
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return CoreVaultService.create_folder(
        db=db,
        tenant_id=str(current_user.tenant_id),
        owner_id=str(current_user.id),
        name=name,
        parent_id=parent_id,
        is_shared=is_shared,
        description=description
    )

@router.delete("/vault/{document_id}")
def delete_mobile_vault_document(
    document_id: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = CoreVaultService.get_document_by_id(db, document_id, str(current_user.tenant_id))
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if doc.owner_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Only the owner can delete this document")

    success = CoreVaultService.delete_document(db, document_id, str(current_user.tenant_id))
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete document")
        
    return {"status": "success"}

@router.patch("/vault/move")
def move_mobile_vault_documents(
    data: dict,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc_ids = data.get("doc_ids", [])
    target_parent_id = data.get("target_parent_id")
    CoreVaultService.move_documents(db, doc_ids, str(current_user.tenant_id), target_parent_id)
    return {"status": "success"}

@router.patch("/vault/{document_id}/link-transaction")
def link_mobile_vault_document_to_transaction(
    document_id: str,
    data: dict,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    transaction_id = data.get("transaction_id")
    doc = CoreVaultService.link_transaction(db, document_id, str(current_user.tenant_id), transaction_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@router.get("/vault/{document_id}/download")
def download_mobile_vault_document(
    document_id: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = CoreVaultService.get_document_by_id(db, document_id, str(current_user.tenant_id))
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not doc.is_shared and doc.owner_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")

    return FileResponse(
        path=doc.file_path,
        filename=doc.filename,
        media_type=doc.mime_type
    )

@router.get("/vault/{document_id}/thumbnail")
def get_mobile_vault_thumbnail(
    document_id: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = CoreVaultService.get_document_by_id(db, document_id, str(current_user.tenant_id))
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not os.path.exists(doc.thumbnail_path or ""):
        raise HTTPException(status_code=404, detail="Thumbnail not found")

    return FileResponse(path=doc.thumbnail_path, media_type="image/jpeg")

@router.put("/vault/{document_id}")
def update_mobile_vault_document(
    document_id: str,
    filename: Optional[str] = Form(None),
    file_type: Optional[vault_models.DocumentType] = Form(None),
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = CoreVaultService.get_document_by_id(db, document_id, str(current_user.tenant_id))
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if filename is not None:
        doc.filename = filename
    if file_type is not None:
        doc.file_type = file_type
        
    db.commit()
    db.refresh(doc)
    return doc
