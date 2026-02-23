from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
import shutil
import tempfile
import os

from backend.app.core.database import get_db
from backend.app.modules.auth import models as auth_models
from backend.app.modules.auth.dependencies import get_current_user
from backend.app.modules.finance.services.mutual_funds import MutualFundService
from backend.app.modules.ingestion.cas_parser import CASParser
from backend.app.modules.ingestion import models as ingestion_models

router = APIRouter(prefix="/mutual-funds", tags=["Mutual Funds"])

class TransactionCreate(BaseModel):
    scheme_code: str
    type: str = "BUY" # BUY, SELL
    amount: float
    units: float
    nav: float
    date: datetime
    folio_number: Optional[str] = None

@router.post("/sync/refresh")
async def trigger_sync(
    background_tasks: BackgroundTasks,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Trigger background NAV refresh for all holdings"""
    tenant_id = str(current_user.tenant_id)
    # Fire and forget - let it handle its own DB session
    background_tasks.add_task(MutualFundService.refresh_tenant_navs, tenant_id)
    return {"status": "running", "message": "Sync started in background"}

@router.get("/sync/status")
async def get_sync_status(
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get latest sync log for tenant"""
    tenant_id = str(current_user.tenant_id)
    log = MutualFundService.get_latest_sync_status(db, tenant_id)
    if not log:
        return {"status": "idle"}
    
    return {
        "status": log.status,
        "started_at": log.started_at,
        "completed_at": log.completed_at,
        "updated_count": log.num_funds_updated,
        "error": log.error_message
    }

@router.get("/search")
def search_funds(
    q: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    amc: Optional[str] = Query(None),
    limit: int = 20,
    offset: int = 0,
    sort_by: str = Query('relevance')
):
    # Allow empty query to fetch popular/trending funds for the Explore tab
    return MutualFundService.search_funds(query=q, category=category, amc=amc, limit=limit, offset=offset, sort_by=sort_by)

@router.get("/indices")
def get_market_indices():
    return MutualFundService.get_market_indices()

@router.get("/{scheme_code}/nav")
def get_nav(scheme_code: str):
    data = MutualFundService.get_fund_nav(scheme_code)
    if not data:
        raise HTTPException(status_code=404, detail="Scheme not found or API error")
    
    # Extract latest NAV
    if data and data.get("data"):
        latest = data["data"][0] # API returns sorted by date desc
        return {"nav": float(latest["nav"]), "date": latest["date"]}
    
    raise HTTPException(status_code=404, detail="NAV data unavailable")

@router.get("/portfolio")
def get_portfolio(
    user_id: Optional[str] = Query(None),
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return MutualFundService.get_portfolio(db, str(current_user.tenant_id), user_id)

@router.get("/analytics")
def get_analytics(
    user_id: Optional[str] = Query(None),
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return MutualFundService.get_portfolio_analytics(db, str(current_user.tenant_id), user_id)

@router.get("/analytics/performance-timeline")
def get_performance_timeline(
    period: str = "1y",
    granularity: str = "1w",
    user_id: Optional[str] = Query(None),
    scheme_code: Optional[str] = Query(None),
    holding_id: Optional[str] = Query(None),
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get portfolio performance timeline.
    
    Query params:
    - period: One of '1m', '3m', '6m', '1y', 'all'
    - granularity: One of '1d', '1w', '1m'
    - user_id: Filter by specific family member
    - scheme_code: Filter by specific fund scheme
    - holding_id: Filter by specific holding
    """
    return MutualFundService.get_performance_timeline(db, str(current_user.tenant_id), period, granularity, user_id, scheme_code, holding_id)

@router.delete("/analytics/cache")
def clear_timeline_cache(
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Clear timeline cache for current user"""
    count = MutualFundService.clear_timeline_cache(db, str(current_user.tenant_id))
    return {"message": f"Cleared {count} cache entries"}

@router.post("/cleanup-duplicates")
def cleanup_duplicate_orders(
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove duplicate mutual fund orders that might have been imported multiple times"""
    tenant_id = str(current_user.tenant_id)
    removed_count = MutualFundService.cleanup_duplicates(db, tenant_id)
    return {"message": f"Removed {removed_count} duplicate orders and synchronized holdings"}


@router.post("/recalculate-holdings")
def trigger_recalculate_holdings(
    user_id: Optional[str] = Query(None),
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Rebuild holdings table from order history"""
    try:
        count = MutualFundService.recalculate_holdings(db, str(current_user.tenant_id), user_id)
        return {"status": "success", "processed_orders": count}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/holdings/{holding_id}")
def get_holding_details(
    holding_id: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    details = MutualFundService.get_holding_details(db, str(current_user.tenant_id), holding_id)
    if not details:
        # Fallback: if holding_id is numeric, it might be a scheme_code passed from a generic link
        if holding_id.isdigit():
            return get_scheme_details(holding_id, current_user, db)
        raise HTTPException(status_code=404, detail="Holding not found")
    return details

@router.get("/schemes/{scheme_code}/details")
def get_scheme_details(
    scheme_code: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    details = MutualFundService.get_scheme_details(db, str(current_user.tenant_id), scheme_code)
    if not details:
        raise HTTPException(status_code=404, detail="Scheme holdings not found")
    return details

@router.get("/schemes/{scheme_code}/info")
def get_scheme_info(
    scheme_code: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get scheme metadata without requiring an active holding."""
    info = MutualFundService.get_scheme_info(db, str(current_user.tenant_id), scheme_code)
    if not info:
        raise HTTPException(status_code=404, detail="Scheme information not found")
    return info

@router.patch("/holdings/{holding_id}")
def update_holding(
    holding_id: str,
    payload: dict,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    holding = MutualFundService.update_holding(db, str(current_user.tenant_id), holding_id, payload)
    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")
    
    return {"status": "success", "message": "Holding updated"}

@router.post("/transaction")
def add_transaction(
    payload: TransactionCreate,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        data = payload.dict()
        # Default attribution to the user who added it
        if "user_id" not in data or not data["user_id"]:
            data["user_id"] = current_user.id
            
        order = MutualFundService.add_transaction(db, str(current_user.tenant_id), data)
        return {"status": "success", "order_id": order.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/holdings/{holding_id}")
def delete_holding(
    holding_id: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        MutualFundService.delete_holding(db, str(current_user.tenant_id), holding_id)
        return {"status": "success", "message": "Holding deleted"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/preview-cas-pdf")
def preview_cas_pdf(
    file: UploadFile = File(...),
    password: str = Form(...),
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Parse PDF and return mapped transactions for review."""
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            shutil.copyfileobj(file.file, tmp)
            temp_path = tmp.name
        # File is now closed, safe to read on Windows
        
        # 1. Parse raw transactions
        raw_transactions = CASParser.parse_pdf(temp_path, password)
        
        # 2. Map to schemes
        mapped_transactions = MutualFundService.map_transactions_to_schemes(raw_transactions)
        
        # 3. Check for duplicates
        tenant_id = str(current_user.tenant_id)
        for txn in mapped_transactions:
            if 'user_id' not in txn:
                txn['user_id'] = current_user.id
        
        mapped_transactions = MutualFundService.check_duplicates(db, tenant_id, mapped_transactions)
        
        return {
            "transactions": mapped_transactions,
            "total_found": len(raw_transactions)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except: pass

@router.post("/preview-cas-email")
def preview_cas_email(
    password: str = Form(...),
    email_config_id: Optional[str] = Form(None),
    period: Optional[str] = Form(None),
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Scan emails for CAS and return mapped transactions for review."""
    from datetime import datetime
    
    # Find email config
    query = db.query(ingestion_models.EmailConfiguration).filter(
        ingestion_models.EmailConfiguration.tenant_id == str(current_user.tenant_id)
    )
    if email_config_id:
        query = query.filter(ingestion_models.EmailConfiguration.id == email_config_id)
    
    config = query.first()
    if not config:
        raise HTTPException(status_code=404, detail="No email configuration found")
    
    # Handle period-based timestamp reset
    if period:
        from datetime import timedelta
        now = datetime.utcnow()
        if period == '3m':
            config.cas_last_sync_at = now - timedelta(days=90)
        elif period == '6m':
            config.cas_last_sync_at = now - timedelta(days=180)
        elif period == '1y':
            config.cas_last_sync_at = now - timedelta(days=365)
        elif period == 'all':
            config.cas_last_sync_at = None
        db.flush()

    # 1. Scan emails for raw transactions
    raw_transactions = CASParser.scan_cas_emails(config, password)
    
    # 2. Map to schemes
    mapped_transactions = MutualFundService.map_transactions_to_schemes(raw_transactions)
    
    # 3. Check for duplicates
    tenant_id = str(current_user.tenant_id)
    for txn in mapped_transactions:
        if 'user_id' not in txn:
            txn['user_id'] = current_user.id
    
    mapped_transactions = MutualFundService.check_duplicates(db, tenant_id, mapped_transactions)
    
    return {
        "transactions": mapped_transactions,
        "total_found": len(raw_transactions)
    }

@router.post("/confirm-import")
def confirm_import(
    transactions: List[dict],
    user_id: Optional[str] = Query(None),
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Finalize import for selected transactions."""
    tenant_id = str(current_user.tenant_id)
    
    # Enrich transactions with user_id
    for txn in transactions:
        if user_id:
            txn['user_id'] = user_id
        elif 'user_id' not in txn:
            txn['user_id'] = current_user.id
            
    stats = MutualFundService.import_mapped_transactions(db, tenant_id, transactions)
    
    # Update last sync timestamp if email source used
    if stats["processed"] > 0:
        is_email = any(t.get('import_source') == 'EMAIL' for t in transactions)
        if is_email:
            config = db.query(ingestion_models.EmailConfiguration).filter(
                ingestion_models.EmailConfiguration.tenant_id == tenant_id
            ).first()
            if config:
                from datetime import datetime
                config.cas_last_sync_at = datetime.utcnow()
                db.commit()

    return stats

@router.post("/import-cas")
def import_cas_pdf(
    file: UploadFile = File(...),
    password: str = Form(...),
    user_id: Optional[str] = Form(None),
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Legacy compatibility: Import PDF in one go."""
    # Corrected arguments: must pass current_user and db explicitly
    preview = preview_cas_pdf(file, password, current_user, db)
    mapped_txns = preview["transactions"]
    for txn in mapped_txns:
        txn['import_source'] = 'PDF'
    
    return confirm_import(mapped_txns, user_id, current_user, db)

@router.post("/import-cas-email")
def trigger_cas_email_import(
    password: str = Form(...),
    email_config_id: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None),
    period: Optional[str] = Form(None),
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Legacy compatibility: Sync Email in one go."""
    preview = preview_cas_email(password, email_config_id, period, current_user, db)
    mapped_txns = preview["transactions"]
    for txn in mapped_txns:
        txn['import_source'] = 'EMAIL'
        
    return confirm_import(mapped_txns, user_id, current_user, db)
