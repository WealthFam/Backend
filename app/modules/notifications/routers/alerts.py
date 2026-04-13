from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.core.database import get_db
from backend.app.modules.auth.dependencies import get_current_active_user
from backend.app.modules.notifications import models, schemas

router = APIRouter()

@router.get("/", response_model=schemas.AlertList)
def get_alerts(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user),
    limit: int = Query(20, gt=0, le=100),
    skip: int = Query(0, ge=0)
):
    """
    Fetch historical notifications for the family dashboard.
    Enveloped format followed as per PRACTICES.md.
    """
    from sqlalchemy import or_
    query = db.query(models.Alert).filter(
        models.Alert.tenant_id == current_user.tenant_id,
        or_(models.Alert.user_id == str(current_user.id), models.Alert.user_id == None)
    )
    
    total = query.count()
    alerts = query.order_by(models.Alert.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "data": alerts,
        "total": total
    }

@router.post("/{alert_id}/read")
def mark_alert_as_read(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Mark a specific alert as read."""
    alert = db.query(models.Alert).filter(
        models.Alert.id == alert_id,
        models.Alert.tenant_id == current_user.tenant_id
    ).first()
    
    if alert:
        alert.is_read = True
        db.commit()
        
    return {"status": "success"}
