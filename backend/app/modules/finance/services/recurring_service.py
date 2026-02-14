from typing import List, Optional
from datetime import datetime
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session
from backend.app.modules.finance import models, schemas

class RecurringService:
    @staticmethod
    def create_recurring_transaction(db: Session, recurrence: schemas.RecurringTransactionCreate, tenant_id: str) -> models.RecurringTransaction:
        db_rec = models.RecurringTransaction(
            **recurrence.model_dump(),
            tenant_id=tenant_id
        )
        db.add(db_rec)
        db.commit()
        db.refresh(db_rec)
        return db_rec

    @staticmethod
    def get_recurring_transactions(db: Session, tenant_id: str, user_id: str = None) -> List[models.RecurringTransaction]:
        if user_id in [None, "null", "undefined", ""]:
            user_id = None
        query = db.query(models.RecurringTransaction).filter(
            models.RecurringTransaction.tenant_id == tenant_id
        )
        if user_id:
            from sqlalchemy import or_
            query = query.join(models.Account, models.RecurringTransaction.account_id == models.Account.id).filter(
                or_(models.Account.owner_id == user_id, models.Account.owner_id == None)
            )
        return query.all()

    @staticmethod
    def update_recurring_transaction(db: Session, recurrence_id: str, update: schemas.RecurringTransactionUpdate, tenant_id: str) -> Optional[models.RecurringTransaction]:
        db_rec = db.query(models.RecurringTransaction).filter(
            models.RecurringTransaction.id == recurrence_id,
            models.RecurringTransaction.tenant_id == tenant_id
        ).first()
        
        if not db_rec: return None
        
        data = update.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(db_rec, k, v)
            
        db.commit()
        db.refresh(db_rec)
        return db_rec

    @staticmethod
    def delete_recurring_transaction(db: Session, recurrence_id: str, tenant_id: str) -> bool:
        db_rec = db.query(models.RecurringTransaction).filter(
            models.RecurringTransaction.id == recurrence_id,
            models.RecurringTransaction.tenant_id == tenant_id
        ).first()
        
        if not db_rec: return False
        db.delete(db_rec)
        db.commit()
        return True

    @staticmethod
    def process_recurring_transactions(db: Session, tenant_id: str) -> int:
        """
        Checks for due recurring transactions and generates them.
        Returns count of generated transactions.
        """
        # Fetch active due items
        due_items = db.query(models.RecurringTransaction).filter(
            models.RecurringTransaction.tenant_id == tenant_id,
            models.RecurringTransaction.is_active == True,
            models.RecurringTransaction.next_run_date <= datetime.utcnow()
        ).all()
        
        count = 0
        
        for item in due_items:
            # Generate Transaction
            txn = models.Transaction(
                tenant_id=tenant_id,
                account_id=item.account_id,
                amount=item.amount,
                date=item.next_run_date, # Use the scheduled date, not "now"
                description=item.name,
                recipient=item.name,
                category=item.category,
                type=item.type,
                source="RECURRING",
                external_id=f"rec_{item.id}_{item.next_run_date.strftime('%Y%m%d')}", # De-dup key
                exclude_from_reports=item.exclude_from_reports
            )
            
            exists = db.query(models.Transaction).filter(
                models.Transaction.tenant_id == tenant_id,
                models.Transaction.external_id == txn.external_id
            ).first()
            
            if not exists:
                db.add(txn)
                # Update Account Balance
                acc = db.query(models.Account).filter(models.Account.id == item.account_id).first()
                if acc:
                     acc.balance = (acc.balance or 0) + item.amount
                
                count += 1
                item.last_run_date = datetime.utcnow()
            
            # Update Next Run Date
            next_date = item.next_run_date
            if item.frequency == models.Frequency.DAILY:
                next_date += relativedelta(days=1)
            elif item.frequency == models.Frequency.WEEKLY:
                next_date += relativedelta(weeks=1)
            elif item.frequency == models.Frequency.MONTHLY:
                next_date += relativedelta(months=1)
            elif item.frequency == models.Frequency.YEARLY:
                next_date += relativedelta(years=1)
            
            item.next_run_date = next_date
            
        db.commit()
        return count
