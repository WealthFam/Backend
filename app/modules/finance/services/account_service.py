import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from backend.app.core.database import db_write_lock
from backend.app.core import timezone
from backend.app.modules.finance import models, schemas

logger = logging.getLogger(__name__)

class AccountService:
    @staticmethod
    def create_account(db: Session, account: schemas.AccountCreate, tenant_id: str) -> models.Account:
        with db_write_lock:
            data = account.model_dump()
        if not data.get('tenant_id'):
            data['tenant_id'] = tenant_id
            
        db_account = models.Account(**data)
        if hasattr(db_account, 'owner_id') and db_account.owner_id:
             db_account.owner_id = str(db_account.owner_id) # Ensure string

        # Anchor the initial balance if provided
        if db_account.balance is not None:
             db_account.last_synced_balance = db_account.balance
             db_account.last_synced_at = timezone.utcnow()
             if db_account.credit_limit:
                 db_account.last_synced_limit = db_account.credit_limit

        db.add(db_account)
        db.flush() # Get ID for snapshot
        
        # Create initial snapshot
        if db_account.balance is not None:
            snapshot = models.BalanceSnapshot(
                account_id=str(db_account.id),
                tenant_id=tenant_id,
                balance=db_account.balance,
                credit_limit=db_account.credit_limit,
                timestamp=db_account.last_synced_at,
                source="INITIAL_CREATION"
            )
            db.add(snapshot)
        db.commit()
        db.refresh(db_account)
        
        # Trigger Notification
        try:
            from backend.app.modules.notifications.services import NotificationService
            NotificationService.notify_new_account(
                db, 
                tenant_id, 
                db_account.name, 
                db_account.type.value if hasattr(db_account.type, 'value') else db_account.type
            )
        except Exception as e:
            logger.error(f"Failed to trigger new account notification: {e}")

        return db_account

    @staticmethod
    def get_accounts(db: Session, tenant_id: str, owner_id: Optional[str] = None, user_role: str = "ADULT", include_unverified: bool = False) -> List[models.Account]:
        if owner_id in [None, "null", "undefined", ""]:
            owner_id = None
        
        query = db.query(models.Account).filter(models.Account.tenant_id == tenant_id)
        
        # Only filter out unverified accounts if not explicitly requested
        if not include_unverified:
            query = query.filter(models.Account.is_verified == True)
        
        if owner_id:
            query = query.filter((models.Account.owner_id == owner_id) | (models.Account.owner_id == None))
        
        # Role-based restriction: Kids can't see Investments or Credit Cards
        if user_role == "CHILD":
            query = query.filter(models.Account.type.notin_(["INVESTMENT", "CREDIT"]))
            
        accounts = query.all()
        
        # Populate linked goals
        try:
            # Query for (account_id, goal_name) pairs
            links = db.query(models.GoalAsset.linked_account_id, models.InvestmentGoal.name)\
                .join(models.InvestmentGoal, models.GoalAsset.goal_id == models.InvestmentGoal.id)\
                .filter(models.GoalAsset.linked_account_id.in_([str(a.id) for a in accounts]))\
                .all()
                
            links_map = {}
            for acc_id, goal_name in links:
                if acc_id not in links_map:
                    links_map[acc_id] = []
                links_map[acc_id].append(goal_name)
                
            # Convert to dict and add linked_goals
            account_dicts = []
            for acc in accounts:
                acc_dict = schemas.AccountRead.model_validate(acc).model_dump()
                acc_dict['linked_goals'] = links_map.get(str(acc.id), [])
                account_dicts.append(acc_dict)
                
            return account_dicts
            
        except Exception as e:
            logger.error(f"Error fetching linked goals: {e}")
            return accounts

    @staticmethod
    def update_account(db: Session, account_id: str, account_update: schemas.AccountUpdate, tenant_id: str) -> Optional[models.Account]:
        db_account = db.query(models.Account).filter(
            models.Account.id == account_id,
            models.Account.tenant_id == tenant_id
        ).first()
        
        if not db_account:
            return None
            
        update_data = account_update.model_dump(exclude_unset=True)
        if not update_data:
            return db_account
        
        # Apply updates
        # SECURITY: Prevent balance/limit updates via generic endpoint to enforce Anchoring logic.
        # These must be updated via override_balance or ingestion.
        restricted_fields = ['balance', 'credit_limit', 'last_synced_balance', 'last_synced_at', 'last_synced_limit']
        for field in restricted_fields:
            if field in update_data:
                del update_data[field]
                
        for key, value in update_data.items():
            if key in ['tenant_id', 'owner_id'] and value:
                value = str(value)
            setattr(db_account, key, value)
        
        try:
            db.commit()
            db.refresh(db_account)
            return db_account
        except Exception as e:
            db.rollback()
            # DuckDB limitation: Cannot update accounts that have transactions
            pass
            raise

    @staticmethod
    def delete_account(db: Session, account_id: str, tenant_id: str) -> bool:
        db_account = db.query(models.Account).filter(
            models.Account.id == account_id,
            models.Account.tenant_id == tenant_id
        ).first()
        
        if not db_account:
            return False
            
        db.delete(db_account)
        db.commit()
    @staticmethod
    def override_balance(db: Session, account_id: str, balance: float, timestamp: datetime, tenant_id: str, 
                         credit_limit: Optional[float] = None, source: str = "MANUAL") -> models.Account:
        with db_write_lock:
            db_account = db.query(models.Account).filter(
            models.Account.id == account_id,
            models.Account.tenant_id == tenant_id
        ).first()
        
        if not db_account:
            raise ValueError("Account not found")
        
        # 1. Update Account anchoring
        db_account.balance = balance
        db_account.last_synced_balance = balance
        db_account.last_synced_at = timestamp
        if credit_limit is not None:
            db_account.credit_limit = credit_limit
            db_account.last_synced_limit = credit_limit
        
        # 2. Add Snapshot
        snapshot = models.BalanceSnapshot(
            account_id=account_id,
            tenant_id=tenant_id,
            balance=balance,
            timestamp=timestamp,
            source=source
        )
        db.add(snapshot)
        db.commit()
        db.refresh(db_account)
        return db_account
