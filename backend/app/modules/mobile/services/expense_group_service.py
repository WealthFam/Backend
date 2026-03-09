from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from backend.app.modules.finance import models, schemas as finance_schemas

class MobileExpenseGroupService:
    @staticmethod
    def calculate_total_spend(db: Session, group: models.ExpenseGroup, tenant_id: str, user_id: str = None) -> float:
        # Subquery/Query for this specific group's total
        amt_query = db.query(func.sum(models.Transaction.amount)).filter(
            models.Transaction.expense_group_id == str(group.id),
            models.Transaction.tenant_id == tenant_id,
            models.Transaction.exclude_from_reports == False,
            models.Transaction.is_transfer == False
        )
        
        if group.start_date:
            amt_query = amt_query.filter(models.Transaction.date >= group.start_date)
        if group.end_date:
            # Same end of day logic
            e_date = group.end_date
            if hasattr(e_date, 'replace'):
                e_date = e_date.replace(hour=23, minute=59, second=59)
            amt_query = amt_query.filter(models.Transaction.date <= e_date)

        if user_id:
            amt_query = amt_query.join(models.Account, models.Transaction.account_id == models.Account.id)\
                                 .filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))
        
        total_amt = amt_query.scalar()
        return float(-(total_amt or 0))

    @staticmethod
    def get_expense_group(db: Session, group_id: str, tenant_id: str, user_id: str = None) -> Optional[models.ExpenseGroup]:
        group = db.query(models.ExpenseGroup).filter(
            models.ExpenseGroup.id == group_id,
            models.ExpenseGroup.tenant_id == tenant_id
        ).first()
        
        if group:
            group.total_spend = MobileExpenseGroupService.calculate_total_spend(db, group, tenant_id, user_id)
            
        return group

    @staticmethod
    def get_expense_groups(db: Session, tenant_id: str, user_id: str = None) -> List[models.ExpenseGroup]:
        # Fetch all groups for this tenant
        groups = db.query(models.ExpenseGroup).filter(
            models.ExpenseGroup.tenant_id == tenant_id
        ).all()
        
        if not groups:
            return []
            
        for group in groups:
            group.total_spend = MobileExpenseGroupService.calculate_total_spend(db, group, tenant_id, user_id)
            
        return groups

    @staticmethod
    def link_transactions(db: Session, group_id: str, transaction_ids: List[str], tenant_id: str) -> int:
        db_group = db.query(models.ExpenseGroup).filter(
            models.ExpenseGroup.id == group_id,
            models.ExpenseGroup.tenant_id == tenant_id
        ).first()
        if not db_group:
            return 0
            
        count = db.query(models.Transaction).filter(
            models.Transaction.id.in_(transaction_ids),
            models.Transaction.tenant_id == tenant_id
        ).update({models.Transaction.expense_group_id: group_id}, synchronize_session=False)
        
        db.commit()
        return count

    @staticmethod
    def unlink_transactions(db: Session, group_id: str, transaction_ids: List[str], tenant_id: str) -> int:
        count = db.query(models.Transaction).filter(
            models.Transaction.id.in_(transaction_ids),
            models.Transaction.expense_group_id == group_id,
            models.Transaction.tenant_id == tenant_id
        ).update({models.Transaction.expense_group_id: None}, synchronize_session=False)
        
        db.commit()
        return count

    @staticmethod
    def create_expense_group(db: Session, group: finance_schemas.ExpenseGroupCreate, tenant_id: str) -> models.ExpenseGroup:
        db_group = models.ExpenseGroup(
            **group.model_dump(),
            tenant_id=tenant_id
        )
        db.add(db_group)
        db.commit()
        db.refresh(db_group)
        return db_group

    @staticmethod
    def update_expense_group(db: Session, group_id: str, update: finance_schemas.ExpenseGroupUpdate, tenant_id: str) -> Optional[models.ExpenseGroup]:
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
            
        db.delete(db_group)
        db.commit()
        return True
