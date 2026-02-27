from datetime import datetime
from backend.app.core import timezone
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.modules.finance import models

class MobileService:
    @staticmethod
    def get_mobile_summary(db: Session, tenant_id: str, user_id: str = None):
        """Lightweight endpoint for mobile notifications - only returns essential data"""
        
        # 1. Today's total spending
        today_start = timezone.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_query = db.query(func.sum(models.Transaction.amount)).filter(
            models.Transaction.tenant_id == tenant_id,
            models.Transaction.amount < 0,
            models.Transaction.is_transfer == False,
            models.Transaction.date >= today_start
        )
        
        if user_id:
            from sqlalchemy import or_
            today_query = today_query.join(
                models.Account, models.Transaction.account_id == models.Account.id
            ).filter(
                or_(models.Account.owner_id == user_id, models.Account.owner_id == None)
            )
        
        today_total = abs(float(today_query.scalar() or 0))
        
        # 2. Month's total spending
        month_start = datetime(timezone.utcnow().year, timezone.utcnow().month, 1)
        month_query = db.query(func.sum(models.Transaction.amount)).filter(
            models.Transaction.tenant_id == tenant_id,
            models.Transaction.amount < 0,
            models.Transaction.is_transfer == False,
            models.Transaction.date >= month_start
        )
        
        if user_id:
            from sqlalchemy import or_
            month_query = month_query.join(
                models.Account, models.Transaction.account_id == models.Account.id
            ).filter(
                or_(models.Account.owner_id == user_id, models.Account.owner_id == None)
            )
        
        monthly_total = abs(float(month_query.scalar() or 0))
        
        # 3. Latest transaction
        latest_query = db.query(models.Transaction).filter(
            models.Transaction.tenant_id == tenant_id,
            models.Transaction.amount < 0,
            models.Transaction.is_transfer == False
        )
        
        if user_id:
            from sqlalchemy import or_
            latest_query = latest_query.join(
                models.Account, models.Transaction.account_id == models.Account.id
            ).filter(
                or_(models.Account.owner_id == user_id, models.Account.owner_id == None)
            )
        
        latest_txn = latest_query.order_by(models.Transaction.date.desc()).first()
        
        latest_transaction = None
        if latest_txn:
            latest_transaction = {
                "amount": abs(float(latest_txn.amount)),
                "description": latest_txn.description,
                "time": latest_txn.date.strftime("%H:%M") if latest_txn.date else ""
            }
        
        return {
            "today_total": today_total,
            "monthly_total": monthly_total,
            "latest_transaction": latest_transaction
        }
