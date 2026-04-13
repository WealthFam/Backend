from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.modules.finance import models, schemas

class ExpenseGroupService:
    @staticmethod
    def get_expense_groups(db: Session, tenant_id: str, user_id: str = None) -> List[models.ExpenseGroup]:
        # 1. Fetch all groups
        groups = db.query(models.ExpenseGroup).filter(
            models.ExpenseGroup.tenant_id == tenant_id
        ).all()
        
        if not groups:
            return []
            
        # 2. Fetch totals in bulk
        # select expense_group_id, sum(amount) from transactions where expense_group_id IN (...) group by expense_group_id
        group_ids = [g.id for g in groups]
        
        query = db.query(
            models.Transaction.expense_group_id,
            func.sum(models.Transaction.amount)
        ).filter(
            models.Transaction.expense_group_id.in_(group_ids),
            models.Transaction.tenant_id == tenant_id
        )
        
        if user_id:
            from sqlalchemy import or_
            query = query.join(models.Account, models.Transaction.account_id == models.Account.id)\
                         .filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))
            
        totals = query.group_by(models.Transaction.expense_group_id).all()
        
        # 3. Map totals (Negate because expenses are typically stored as negative)
        totals_map = {gid: -float(total or 0) for gid, total in totals}
        
        # 4. Assign to model instances (using setattr to avoid schema validation errors if strict)
        for group in groups:
            group.total_spend = totals_map.get(group.id, 0.0)
            
        return groups

    @staticmethod
    def create_expense_group(db: Session, group: schemas.ExpenseGroupCreate, tenant_id: str) -> models.ExpenseGroup:
        db_group = models.ExpenseGroup(
            **group.model_dump(),
            tenant_id=tenant_id
        )
        db.add(db_group)
        db.commit()
        db.refresh(db_group)
        return db_group

    @staticmethod
    def update_expense_group(db: Session, group_id: str, update: schemas.ExpenseGroupUpdate, tenant_id: str) -> Optional[models.ExpenseGroup]:
        db_group = db.query(models.ExpenseGroup).filter(
            models.ExpenseGroup.id == group_id,
            models.ExpenseGroup.tenant_id == tenant_id
        ).first()
        
        if not db_group:
            return None
            
        data = update.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(db_group, k, v)
            
        db.commit()
        db.refresh(db_group)
        return db_group

    @staticmethod
    def delete_expense_group(db: Session, group_id: str, tenant_id: str) -> bool:
        db_group = db.query(models.ExpenseGroup).filter(
            models.ExpenseGroup.id == group_id,
            models.ExpenseGroup.tenant_id == tenant_id
        ).first()
        
        if not db_group:
            return False
            
        # Optional: Decide what to do with transactions in this group. 
        # For now, we'll just let them have an orphaned expense_group_id or set it to NULL.
        # SQLite/DuckDB foreign keys might need handling if strictly enforced.
        
        db.delete(db_group)
        db.commit()
        return True

    @staticmethod
    def link_transactions(db: Session, group_id: str, transaction_ids: List[str], tenant_id: str) -> int:
        # Verify group exists
        db_group = db.query(models.ExpenseGroup).filter(
            models.ExpenseGroup.id == group_id,
            models.ExpenseGroup.tenant_id == tenant_id
        ).first()
        if not db_group:
            return 0
            
        # Update transactions in bulk
        count = db.query(models.Transaction).filter(
            models.Transaction.id.in_(transaction_ids),
            models.Transaction.tenant_id == tenant_id
        ).update({models.Transaction.expense_group_id: group_id}, synchronize_session=False)
        
        db.commit()
        return count
