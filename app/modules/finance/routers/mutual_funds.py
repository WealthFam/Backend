import os
import shutil
import tempfile
import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from backend.app.core import timezone
from backend.app.core.database import get_db
from backend.app.modules.auth import models as auth_models
from backend.app.modules.auth.dependencies import get_current_user
from backend.app.modules.finance import schemas as finance_schemas
from backend.app.modules.finance.models import MutualFundHolding
from backend.app.modules.finance.services.mutual_funds import MutualFundService
from backend.app.modules.finance.services.benchmarks import BenchmarkService
from backend.app.modules.finance.services.external.market_data import MarketDataService
from backend.app.modules.ingestion.cas_parser import CASParser
from backend.app.modules.ingestion import models as ingestion_models

router = APIRouter(prefix="/mutual-funds", tags=["Mutual Funds"])



@router.post("/sync/refresh")
async def trigger_sync(
    background_tasks: BackgroundTasks,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Trigger background NAV refresh for all holdings"""
    tenant_id = str(current_user.tenant_id)
    # Fire and forget - let it handle its own DB session
    background_tasks.add_task(MutualFundService.refresh_tenant_navs, tenant_id, force=True)
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

@router.get("/search", response_model=finance_schemas.MutualFundSearchResponse)
def search_funds(
    q: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    amc: Optional[str] = Query(None),
    limit: int = 20,
    offset: int = 0,
    sort_by: str = Query('relevance')
):
    # Allow empty query to fetch popular/trending funds for the Explore tab
    funds, total = MutualFundService.search_funds(query=q, category=category, amc=amc, limit=limit, offset=offset, sort_by=sort_by)
    return {
        "data": funds, 
        "total": total,
        "page": (offset // limit) + 1,
        "limit": limit
    }

@router.get("/indices", response_model=finance_schemas.MarketIndexResponse)
async def get_market_indices(period: str = Query("1d")):
    indices = await MarketDataService.get_market_indices(period)
    return {"data": indices}

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

@router.get("/portfolio", response_model=finance_schemas.PortfolioOverviewResponse)
def get_portfolio(
    user_id: Optional[str] = Query(None),
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    tenant_id = str(current_user.tenant_id)
    
    holdings = MutualFundService.get_portfolio(db, tenant_id, user_id)
    
    # Accurate Decimal aggregation (PRACTICES.md Section 11.2)
    total_invested = sum((Decimal(str(h.get('invested_value', '0'))) for h in holdings), Decimal('0'))
    total_current = sum((Decimal(str(h.get('current_value', '0'))) for h in holdings), Decimal('0'))
    total_pl = total_current - total_invested

    # Integrate overall performance metrics
    analytics = MutualFundService.get_portfolio_analytics(db, tenant_id, user_id)
    overall_xirr = analytics.get('xirr') if analytics else None
    
    return {
        "data": holdings,
        "total_invested": total_invested,
        "total_current": total_current,
        "total_pl": total_pl,
        "overall_xirr": overall_xirr
    }


@router.get("/analytics")
def get_analytics(
    user_id: Optional[str] = Query(None),
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return MutualFundService.get_portfolio_analytics(db, str(current_user.tenant_id), user_id)

@router.get("/analytics/performance-timeline")
def get_performance_timeline(
    background_tasks: BackgroundTasks,
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
    """
    tenant_id = str(current_user.tenant_id)
    
    return MutualFundService.get_performance_timeline(db, tenant_id, period, granularity, user_id, scheme_code, holding_id)

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

@router.get("/holdings/{holding_id}/insights")
def get_holding_insights(
    holding_id: str,
    force_refresh: bool = Query(False),
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    tenant_id = str(current_user.tenant_id)
    
    # 1. Distinguish between 404 (Missing Data) and 503 (AI Load/Failure)
    # Check if holding or its aggregated scheme exists
    is_valid_id = False
    try:
        # Check by UUID holding id
        if db.query(MutualFundHolding).filter(MutualFundHolding.id == holding_id, MutualFundHolding.tenant_id == tenant_id, MutualFundHolding.is_deleted == False).first():
            is_valid_id = True
        # Check by scheme code (aggregated view)
        elif holding_id.isdigit() and db.query(MutualFundHolding).filter(MutualFundHolding.scheme_code == holding_id, MutualFundHolding.tenant_id == tenant_id, MutualFundHolding.is_deleted == False).first():
            is_valid_id = True
    except Exception as e:
        logger.error(f"Error validating holding existence for insights: {e}")
        pass

    if not is_valid_id:
        raise HTTPException(status_code=404, detail="Mutual fund holding not found")

    # 2. Attempt AI Generation
    insights = MutualFundService.get_holding_insights(db, tenant_id, holding_id, force_refresh)
    
    if not insights:
        raise HTTPException(
            status_code=503, 
            detail="AI Advisor is currently processing high volume or experiencing temporary downtime. Recent historical insights may be available in cache. Please try again in 1 minute."
        )
        
    return {"insights": insights}

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
    payload: finance_schemas.TransactionCreate,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        data = payload.model_dump()
        # Ensure user_id is passed for correct holding attribution
        data["user_id"] = str(current_user.id)
            
        order = MutualFundService.add_transaction(db, str(current_user.tenant_id), data)
        return {"status": "success", "order_id": order.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/transactions/{transaction_id}")
def update_transaction(
    transaction_id: str,
    payload: finance_schemas.TransactionUpdate,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a specific transaction and trigger recalculation"""
    try:
        MutualFundService.update_transaction(
            db, str(current_user.tenant_id), transaction_id, payload.model_dump(exclude_unset=True)
        )
        return {"status": "success", "message": "Transaction updated and holdings recalculated"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/transactions/bulk-delete")
def bulk_delete_transactions(
    payload: finance_schemas.BulkDeleteRequest,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Soft-delete multiple transactions and trigger recalculate"""
    try:
        count = MutualFundService.bulk_delete_transactions(
            db, str(current_user.tenant_id), payload.transaction_ids
        )
        return {"status": "success", "deleted_count": count}
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
    user_id: Optional[str] = Form(None),
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
        
        tenant_id = str(current_user.tenant_id)
        # 1. Parse raw transactions
        raw_transactions = CASParser.parse_pdf(tenant_id, temp_path, password)
        
        # 2. Map to schemes
        mapped_transactions = MutualFundService.map_transactions_to_schemes(raw_transactions)
        
        # 3. Stamp the correct target user_id BEFORE duplicate check.
        # If the caller specifies a target user (e.g. a different family member),
        # use that so check_duplicates queries the right user's orders.
        effective_user_id = user_id or str(current_user.id)
        tenant_id = str(current_user.tenant_id)
        for txn in mapped_transactions:
            txn['user_id'] = effective_user_id
        
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
    user_id: Optional[str] = Form(None),
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Scan emails for CAS and return mapped transactions for review."""
    
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
        now = timezone.utcnow()
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
    
    # 3. Stamp the correct target user_id BEFORE duplicate check.
    # If the caller specifies a target user (e.g. a different family member),
    # use that so check_duplicates queries the right user's orders.
    effective_user_id = user_id or str(current_user.id)
    tenant_id = str(current_user.tenant_id)
    for txn in mapped_transactions:
        txn['user_id'] = effective_user_id
    
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
                config.cas_last_sync_at = timezone.utcnow()
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
    # Pass user_id to preview so duplicates are checked against the correct user
    preview = preview_cas_pdf(file, password, user_id, current_user, db)
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
    # Pass user_id to preview so duplicates are checked against the correct user
    preview = preview_cas_email(password, email_config_id, period, user_id, current_user, db)
    mapped_txns = preview["transactions"]
    for txn in mapped_txns:
        txn['import_source'] = 'EMAIL'
        
    return confirm_import(mapped_txns, user_id, current_user, db)

@router.get("/analytics/timeline")
async def get_portfolio_timeline(
    days: int = 30,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get historical performance trend for the portfolio"""
    # Baseline implementation
    return {"trend": [], "days": days}

@router.post("/portfolio/insights")
def generate_portfolio_insights(
    user_id: Optional[str] = Query(None),
    force_refresh: bool = Query(False),
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate AI insights for the mutual fund portfolio"""
    tenant_id = str(current_user.tenant_id)
    return {
        "insights": MutualFundService.get_portfolio_insights(db, tenant_id, user_id, force_refresh)
    }

@router.get("/benchmarks/rules", response_model=finance_schemas.MutualFundBenchmarkRulePagination, summary="Fetch benchmark rules", description="Retrieve all category-to-benchmark resolution rules ordered by priority.")
def get_benchmark_rules(
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    rules = BenchmarkService.get_all_rules(db)
    return {"data": rules, "total": len(rules)}

@router.post("/benchmarks/rules", response_model=finance_schemas.MutualFundBenchmarkRuleRead, summary="Save benchmark rule", description="Create a new or update an existing benchmark resolution rule.")
def save_benchmark_rule(
    payload: finance_schemas.MutualFundBenchmarkRuleCreate,
    rule_id: Optional[str] = Query(None, description="ID of the rule to update"),
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return BenchmarkService.save_rule(db, payload.model_dump(), rule_id)

@router.delete("/benchmarks/rules/{rule_id}", summary="Delete benchmark rule", description="Remove a benchmark resolution rule from the database.")
def delete_benchmark_rule(
    rule_id: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        BenchmarkService.delete_rule(db, rule_id)
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/benchmarks/rules/sync", summary="Sync benchmarks", description="Re-calculate benchmark mappings for all funds based on current rules.")
def sync_benchmark_mappings(
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    count = BenchmarkService.recalculate_all_mappings(db)
    # Clear timeline cache as benchmarks have changed
    MutualFundService.clear_timeline_cache(db, str(current_user.tenant_id))
    return {"status": "success", "updated_count": count}
