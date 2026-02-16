from datetime import datetime, timedelta, date
import calendar
import uuid
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.modules.auth import models as auth_models
from backend.app.modules.auth import security, services as auth_services
from backend.app.modules.auth.dependencies import get_current_user
from backend.app.modules.ingestion import models as ingestion_models
from backend.app.modules.ingestion.services import IngestionService
from backend.app.modules.mobile import schemas
from backend.app.modules.notifications import NotificationService, Alert
from backend.app.modules.finance.services.analytics_service import AnalyticsService

router = APIRouter(tags=["Mobile"])

# --- Mobile App Endpoints (API/V1/MOBILE) ---

@router.post("/login", response_model=schemas.MobileLoginResponse)
def mobile_login(
    payload: schemas.MobileLoginRequest,
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
        device.last_seen_at = datetime.utcnow()
        
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
    
    # 3. Issue Long-Lived Token
    # Using 30 days for mobile convenience
    access_token_expires = timedelta(days=30) 
    access_token = security.create_access_token(
        data={"sub": user.email, "tenant_id": str(user.tenant_id), "device_id": device.device_id},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "expires_in": int(access_token_expires.total_seconds()),
        "device_status": device,
        "user_role": user.role
    }

@router.post("/register-device", response_model=schemas.DeviceResponse)
def register_device_manually(
    payload: schemas.DeviceRegister,
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
        device.last_seen_at = datetime.utcnow()
        
    db.commit()
    db.refresh(device)
    return device

@router.get("/status", response_model=schemas.DeviceResponse)
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
        
    return device

@router.post("/heartbeat", response_model=schemas.DeviceResponse)
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
        
    device.last_seen_at = datetime.utcnow()
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
    
    return device

# --- Web Dashboard Management Endpoints (also under /mobile namespace) ---

@router.get("/devices", response_model=List[schemas.DeviceResponse])
def list_devices(
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all registered devices for the tenant (for Web UI).
    """
    return db.query(ingestion_models.MobileDevice).filter(
        ingestion_models.MobileDevice.tenant_id == str(current_user.tenant_id)
    ).order_by(ingestion_models.MobileDevice.last_seen_at.desc()).all()

@router.patch("/devices/{device_id}/approve", response_model=schemas.DeviceResponse)
def approve_device(
    device_id: str,
    payload: schemas.ToggleApprovalRequest,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Toggle device approval status (Web UI only).
    """
    # Authorization check: Only parents can approve? For now, any adult user.
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
    if current_user.role == "CHILD":
       # Optional: Allow user to delete their own device by device_id matching?
       # For now, strict role check or ownership check
       pass

    # Find device by ID or Device_ID (Hybrid lookup for convenience)
    device = db.query(ingestion_models.MobileDevice).filter(
        (ingestion_models.MobileDevice.id == device_id) | (ingestion_models.MobileDevice.device_id == device_id),
        ingestion_models.MobileDevice.tenant_id == str(current_user.tenant_id)
    ).first()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
        
    db.delete(device)
    db.commit()
    return {"status": "deleted"}

@router.patch("/devices/{device_id}", response_model=schemas.DeviceResponse)
def update_device(
    device_id: str,
    payload: schemas.DeviceUpdate,
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

@router.patch("/devices/{device_id}/enable")
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
    device.is_enabled = enabled
    db.commit()
    db.refresh(device)
    return device

@router.patch("/devices/{device_id}/ignore")
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
        device.is_approved = False # Auto-revoke approval if ignored
        

    db.commit()
    db.refresh(device)
    return device

@router.patch("/devices/{device_id}/assign")
def assign_device_user(
    device_id: str,
    payload: schemas.AssignUserRequest,
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

@router.get("/members", response_model=List[schemas.MemberResponse])
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
            "avatar_url": None # Placeholder for now
        }
        for u in users
    ]

@router.get("/dashboard", response_model=schemas.MobileDashboardResponse)
def get_mobile_dashboard(
    month: Optional[int] = None,
    year: Optional[int] = None,
    member_id: Optional[str] = None,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns a lightweight summary for the mobile dashboard with chart data.
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
        
    now = datetime.utcnow()
    target_month = month or now.month
    target_year = year or now.year
    
    start_date = datetime(target_year, target_month, 1)
    last_day = calendar.monthrange(target_year, target_month)[1]
    end_date = datetime(target_year, target_month, last_day, 23, 59, 59)
    
    metrics = AnalyticsService.get_summary_metrics(
        db, 
        str(current_user.tenant_id), 
        user_role=current_user.role,
        user_id=target_user_id, # Can be None for All
        start_date=start_date,
        end_date=end_date,
        exclude_hidden=True
    )
    
    # --- 1. Category Distribution (Pie Chart) ---
    from sqlalchemy import func, or_
    from backend.app.modules.finance import models
    
    cat_query = db.query(
        models.Transaction.category,
        func.sum(models.Transaction.amount).label('total')
    ).filter(
        models.Transaction.tenant_id == str(current_user.tenant_id),
        models.Transaction.amount < 0,
        models.Transaction.is_transfer == False,
        models.Transaction.exclude_from_reports == False,
        models.Transaction.date >= start_date,
        models.Transaction.date <= end_date
    )
    
    if target_user_id:
        cat_query = cat_query.join(
            models.Account, models.Transaction.account_id == models.Account.id
        ).filter(
            or_(models.Account.owner_id == target_user_id, models.Account.owner_id == None)
        )
    
    cat_results = cat_query.group_by(models.Transaction.category).order_by(func.sum(models.Transaction.amount).asc()).all()
    
    category_distribution = [
        schemas.CategoryPieItem(name=cat[0], value=abs(float(cat[1])))
        for cat in cat_results
    ]
    
    # --- 2. Daily Spending Trend (Bar/Line Chart) ---
    total_budget = metrics["budget_health"]["limit"]
    daily_budget_limit = total_budget / last_day if total_budget > 0 else 0
    
    trend_query = db.query(
        func.date(models.Transaction.date).label('day'),
        func.sum(models.Transaction.amount).label('total')
    ).filter(
        models.Transaction.tenant_id == str(current_user.tenant_id),
        models.Transaction.amount < 0,
        models.Transaction.is_transfer == False,
        models.Transaction.exclude_from_reports == False,
        models.Transaction.date >= start_date,
        models.Transaction.date <= end_date
    )
    
    if target_user_id:
        trend_query = trend_query.join(
            models.Account, models.Transaction.account_id == models.Account.id
        ).filter(
            or_(models.Account.owner_id == target_user_id, models.Account.owner_id == None)
        )
    
    trend_results = trend_query.group_by(func.date(models.Transaction.date)).all()
    trend_map = {str(row.day): abs(float(row.total)) for row in trend_results}
    
    spending_trend = []
    for day in range(1, last_day + 1):
        d_date = date(target_year, target_month, day)
        d_str = d_date.isoformat()
        spending_trend.append(schemas.SpendingTrendItem(
            date=d_str,
            amount=trend_map.get(d_str, 0.0),
            daily_limit=daily_budget_limit
        ))
        
    # --- 3. Pending Triage Count ---
    pending_count = db.query(ingestion_models.PendingTransaction).filter(
        ingestion_models.PendingTransaction.tenant_id == str(current_user.tenant_id)
    ).count()

    # Filter recent transactions to match dashboard logic (Safe display)
    # Filtered by service
    filtered_recent = metrics["recent_transactions"]

    return {
        "summary": {
            "today_total": metrics["today_total"],
            "monthly_total": metrics["monthly_total"],
            "currency": metrics["currency"]
        },
        "budget": metrics["budget_health"],
        "spending_trend": spending_trend,
        "category_distribution": category_distribution,
        "recent_transactions": [
            {
                **txn,
                "account_name": db.query(models.Account.name).filter(models.Account.id == txn['account_id']).scalar()
            }
            for txn in filtered_recent
        ],
        "pending_triage_count": pending_count
    }

@router.get("/triage", response_model=List[schemas.RecentTransaction])
def list_mobile_triage(
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all pending transactions for the mobile app to review.
    """
    from backend.app.modules.finance.services.transaction_service import TransactionService
    items, total = TransactionService.get_pending_transactions(
        db, str(current_user.tenant_id), limit=100, sort_order="desc"
    )
    
    enriched = []
    from backend.app.modules.finance import models
    for txn in items:
        # Use relationship for owner info
        owner_name = "Unknown"
        if txn.account and txn.account.owner:
            owner_name = txn.account.owner.full_name or "Unknown"

        enriched.append({
            "id": txn.id,
            "date": txn.date,
            "description": txn.description or "Review Required",
            "amount": float(txn.amount),
            "category": txn.category,
            "account_name": txn.account.name if txn.account else "Unknown",
            "account_owner_name": owner_name
        })
    return enriched

@router.get("/transactions", response_model=schemas.TransactionResponse)
def list_mobile_transactions(
    page: int = 1,
    page_size: int = 20,
    month: Optional[int] = None,
    year: Optional[int] = None,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Paginated transactions list for infinite scroll.
    """
    from backend.app.modules.finance import models
    from sqlalchemy import or_
    
    query = db.query(models.Transaction).options(
        joinedload(models.Transaction.account)
    ).filter(
        models.Transaction.tenant_id == str(current_user.tenant_id),
        models.Transaction.is_transfer == False,
        models.Transaction.exclude_from_reports == False
    )
    
    # Filter by user ownership
    query = query.join(
        models.Account, models.Transaction.account_id == models.Account.id
    ).filter(
        or_(models.Account.owner_id == str(current_user.id), models.Account.owner_id == None)
    )
    
    if month and year:
        start_date = datetime(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        end_date = datetime(year, month, last_day, 23, 59, 59)
        query = query.filter(models.Transaction.date >= start_date, models.Transaction.date <= end_date)
        
    total_count = query.count()
    
    transactions = query.order_by(models.Transaction.date.desc()) \
                        .offset((page - 1) * page_size) \
                        .limit(page_size) \
                        .all()
                        
    # Enrich with owner info (simplified) or mapped
    enriched = []
    for txn in transactions:
        # Use relationship for owner info
        owner_name = None
        if txn.account and txn.account.owner:
            owner_name = txn.account.owner.full_name

        enriched.append({
            "id": txn.id,
            "date": txn.date,
            "description": txn.description,
            "amount": float(txn.amount),
            "category": txn.category,
            "account_name": txn.account.name if txn.account else "Unknown",
            "account_owner_name": owner_name
        })
        
    has_next = (page * page_size) < total_count
    
    return {
        "items": enriched,
        "next_page": page + 1 if has_next else None
    }
    
class CreateTransactionRequest(BaseModel):
    account_id: str
    amount: float
    description: str
    category: str
    date: str

@router.post("/transactions", response_model=schemas.RecentTransaction)
def create_mobile_transaction(
    payload: CreateTransactionRequest,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new transaction (manual entry).
    """
    from backend.app.modules.finance import models
    from datetime import datetime
    
    # Verify account ownership
    account = db.query(models.Account).filter(
         models.Account.id == payload.account_id,
         or_(models.Account.owner_id == str(current_user.id), models.Account.owner_id == None),
         models.Account.tenant_id == str(current_user.tenant_id)
    ).first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found or access denied")
        
    txn = models.Transaction(
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

@router.get("/funds", response_model=schemas.MobileFundsResponse)
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
        
        clean_holdings.append(schemas.FundHolding(
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

@router.get("/categories", response_model=List[schemas.Category])
def get_categories(
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from backend.app.modules.finance.services.category_service import CategoryService
    cats = CategoryService.get_categories(db, str(current_user.tenant_id))
    return [
        schemas.Category(id=str(c.id), name=c.name, icon=c.icon, type=getattr(c, 'type', 'expense')) 
        for c in cats
    ]

@router.patch("/transactions/{transaction_id}", response_model=schemas.RecentTransaction)
def update_transaction_category(
    transaction_id: str,
    payload: schemas.UpdateTransactionCategoryRequest,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from backend.app.modules.finance import models
    from backend.app.modules.finance.services.category_service import CategoryService
    from backend.app.modules.finance import schemas as finance_schemas
    
    # 1. Update Transaction
    txn = db.query(models.Transaction).filter(
        models.Transaction.id == transaction_id,
        models.Transaction.tenant_id == str(current_user.tenant_id)
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
def get_mobile_alerts(
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
        body=f"Sent to {device.device_name} at {datetime.now().strftime('%H:%M:%S')}",
        user_id=device.user_id,
        category="INFO"
    )
    
    return {"status": "sent", "message": "Test alert created"}
