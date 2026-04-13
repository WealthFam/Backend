import calendar
import uuid
import logging
import traceback
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict

from fastapi import APIRouter, Depends, HTTPException, status
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

    def enrich_txn(txn):
        ext = {
            "account_name": account_map.get(txn['account_id']).name if account_map.get(txn['account_id']) else "Unknown",
            "has_documents": linked_doc_counts.get(txn['id'], 0) > 0
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

@router.get("/triage", response_model=List[mobile_schemas.RecentTransaction])
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
            "source": txn.source
        })
    return enriched

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
    cat_map = {c.name: c for c in category_objs}
    
    # Filter by user ownership if target_user_id is set
    if target_user_id:
        query = query.join(
            finance_models.Account, finance_models.Transaction.account_id == finance_models.Account.id
        ).filter(
            or_(finance_models.Account.owner_id == target_user_id, finance_models.Account.owner_id == None)
        )

    if expense_group_id:
        query = query.filter(finance_models.Transaction.expense_group_id == expense_group_id)
    
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
            cat_obj = cat_map.get(display_category)
            if cat_obj and cat_obj.parent_id:
                parent = next((c for c in category_objs if c.id == cat_obj.parent_id), None)
                if parent:
                    display_category = f"{parent.name} › {cat_obj.name}"

        enriched.append({
            "id": txn.id,
            "date": txn.date,
            "description": txn.description,
            "amount": float(txn.amount),
            "category": display_category,
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
    
    # Fetch portfolio
    holdings = MutualFundService.get_portfolio(db, str(current_user.tenant_id), target_user_id)
    
    total_invested = 0.0
    total_current = 0.0
    
    clean_holdings = []
    
    today_total_change = 0.0
    
    for h in holdings:
        inv = float(h.get('invested_value', 0))
        cur = float(h.get('current_value', 0))
        
        # Calculate Day Change using Sparkline (Last 2 points)
        # Sparkline is [..., T-2, T-1, T] 
        # But in get_portfolio logic: sparkline = [float(d.get("nav", 0.0)) for d in sparkline_data if d.get("nav")]
        # And it says: sparkline_data.reverse() # Reverse to chronological order (Oldest -> Newest)
        # So sparkline[-1] is Latest NAV, sparkline[-2] is Previous Day NAV
        
        day_change = 0.0
        day_change_limit = 0.0
        
        sparkline = h.get('sparkline', [])
        units = float(h.get('units', 0))
        
        if len(sparkline) >= 2 and units > 0:
            latest_nav = sparkline[-1]
            prev_nav = sparkline[-2]
            day_change = (latest_nav - prev_nav) * units
            
        today_total_change += day_change

        total_invested += inv
        total_current += cur
        
        clean_holdings.append(mobile_schemas.FundHolding(
            scheme_code=h['scheme_code'],
            scheme_name=h['scheme_name'],
            units=units,
            current_value=cur,
            invested_value=inv,
            profit_loss=cur - inv,
            last_updated=h.get('last_updated', ''),
            day_change=day_change,
            day_change_percentage=(day_change / (cur - day_change) * 100) if (cur - day_change) > 0 else 0.0,
            xirr=None 
        ))

    day_change_pct = (today_total_change / (total_current - today_total_change) * 100) if (total_current - today_total_change) > 0 else 0.0
        
    return {
        "total_invested": total_invested,
        "total_current": total_current,
        "total_pl": total_current - total_invested,
        "day_change": today_total_change,
        "day_change_percentage": day_change_pct,
        "xirr": None, 
        "holdings": clean_holdings
    }

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
    List accounts for mobile forensic annotation.
    """
    from backend.app.modules.finance.services.account_service import AccountService
    accounts = AccountService.get_accounts(db, str(current_user.tenant_id), user_role=current_user.role)
    return {"data": accounts}

@router.get("/ai/forensic-parse")
def ai_forensic_parse(
    content: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    AI-driven transaction extraction from raw SMS content.
    Used for mobile forensic annotation.
    """
    try:
        result = AIService.auto_parse_transaction(db, str(current_user.tenant_id), content)
        if not result:
            return {"amount": 0.0, "description": "", "category": "Uncategorized", "type": "DEBIT"}
        
        return {
            "amount": result.get("amount", 0.0),
            "description": result.get("recipient", ""),
            "category": result.get("category", "Uncategorized"),
            "type": result.get("type", "DEBIT"),
            "date": result.get("date"),
            "account_mask": result.get("account_mask")
        }
    except Exception as e:
        detail = str(e)
        status_code = 500
        
        if "RESOURCE_EXHAUSTED" in detail or "429" in detail:
            status_code = 429
            detail = "AI quota exceeded. Please try again in a few seconds."
            logger.warning(f"AI Quota Exceeded for user {current_user.id}")
        else:
            logger.error(f"AI Forensic Parse Error: {e}")
            logger.error(traceback.format_exc())
            
        raise HTTPException(status_code=status_code, detail=detail)

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
