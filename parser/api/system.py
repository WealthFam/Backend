from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from parser.db.database import get_db
from parser.db.models import RequestLog
from parser.core.auth import get_current_tenant
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["System"])

@router.get("/health")
def health_check():
    return {"status": "ok", "service": "parser-engine"}

@router.get("/logs")
def list_logs(
    limit: int = 50, 
    offset: int = 0, 
    source: Optional[str] = None, 
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    """
    List ingestion logs with filtering and pagination, scoped to tenant.
    """
    query = db.query(RequestLog).filter(RequestLog.tenant_id == tenant_id)
    
    if source:
        query = query.filter(RequestLog.source == source)
    if status:
        query = query.filter(RequestLog.status == status)
        
    total = query.count()
    logs = query.order_by(RequestLog.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "logs": logs
    }

@router.get("/logs/{log_id}")
def get_log(
    log_id: str, 
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Get detailed logs for a specific request, scoped to tenant.
    """
    log = db.query(RequestLog).filter(
        RequestLog.id == log_id,
        RequestLog.tenant_id == tenant_id
    ).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
        
    return log

@router.post("/migrate-tenant")
def trigger_tenant_migration(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
):
    """
    Forces the single-tenant migration script to run, using the provided authenticated tenant_id.
    This replaces old 'system_tenant' or null records with the real user's tenant_id.
    Called by the main backend on startup to ensure old data is mapped immediately.
    """
    from sqlalchemy import text
    tables_to_update = [
        "request_logs", 
        "file_parsing_configs", 
        "ai_configs", 
        "pattern_rules", 
        "merchant_aliases",
        "ai_call_cache"
    ]
    
    updated_count = 0
    try:
        # We don't need engine connection here, just use the Session
        for table in tables_to_update:
            try:
                res = db.execute(
                    text(f"UPDATE {table} SET tenant_id = :tid WHERE tenant_id = 'system_tenant' OR tenant_id IS NULL"), 
                    {"tid": tenant_id}
                )
                if res.rowcount > 0:
                    updated_count += res.rowcount
                    logger.info(f"Updated {res.rowcount} rows in {table} to tenant '{tenant_id}'")
            except Exception as e:
                logger.warning(f"Warning: could not update {table}: {e}")
                
        db.commit()
        return {"status": "success", "message": f"Migrated {updated_count} records to {tenant_id}"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error during forced tenant migration: {e}")
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")
