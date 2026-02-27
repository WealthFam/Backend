from typing import List, Optional
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session
from backend.app.modules.finance import models, schemas
from backend.app.core import timezone

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
            models.RecurringTransaction.next_run_date <= timezone.utcnow()
        ).all()
        
        count = 0
        
        from backend.app.modules.finance.services.transaction_service import TransactionService
        from backend.app.modules.finance import schemas
        
        for item in due_items:
            # Generate Transaction using Service (handles balance anchoring automatically)
            txn_create = schemas.TransactionCreate(
                account_id=item.account_id,
                amount=item.amount,
                date=item.next_run_date, # Use the scheduled date
                description=item.name,
                recipient=item.name,
                category=item.category,
                source="RECURRING",
                external_id=f"rec_{item.id}_{item.next_run_date.strftime('%Y%m%d')}", # De-dup key
                exclude_from_reports=item.exclude_from_reports
            )
            
            try:
                # We default update_balance=True, letting TransactionService handle the anchor check 
                # (i.e. if date <= last_synced_at, it won't update balance)
                TransactionService.create_transaction(db, txn_create, tenant_id)
                count += 1
                item.last_run_date = timezone.utcnow()
            except ValueError as e:
                # Duplicate transaction? Just move on and update next_run_date to avoid stuck loop
                # checking if it was a dupe error from our service
                if "Duplicate" in str(e):
                    # It already exists, so we mark it as processed to advance the schedule
                    item.last_run_date = timezone.utcnow()
                else:
                    print(f"Error creating recurring transaction {item.id}: {e}")
            except Exception as e:
                print(f"Unexpected error in recurring txn {item.id}: {e}")
                # Don't crash the whole batch
                pass
            
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

    @staticmethod
    def get_recurring_suggestions(db: Session, tenant_id: str) -> List[schemas.RecurringSuggestion]:
        """
        Analyzes transaction history to find recurring patterns (Monthly/Weekly).
        """
        from collections import defaultdict
        import statistics

        # 1. Fetch recent debit transactions (last 6 months)
        six_months_ago = timezone.utcnow() - relativedelta(months=6)
        transactions = db.query(models.Transaction).filter(
            models.Transaction.tenant_id == tenant_id,
            models.Transaction.type == models.TransactionType.DEBIT,
            models.Transaction.date >= six_months_ago,
            models.Transaction.is_transfer == False,
            models.Transaction.is_emi == False
        ).order_by(models.Transaction.date.desc()).all()

        # 2. Group by Recipient + Amount (allowing 5% variance)
        groups = defaultdict(list)
        for t in transactions:
            if not t.recipient and not t.description: continue
            key = t.recipient or t.description
            # We use a slightly fuzzy key (merchant name)
            groups[key.upper()].append(t)

        suggestions = []
        
        # 3. Analyze each group for frequency
        for merchant, txns in groups.items():
            if len(txns) < 3: continue # Need at least 3 occurrences to be a "pattern"

            # Sort by date
            txns.sort(key=lambda x: x.date)
            intervals = []
            for i in range(1, len(txns)):
                diff = (txns[i].date - txns[i-1].date).days
                intervals.append(diff)

            if not intervals: continue

            avg_interval = sum(intervals) / len(intervals)
            std_dev = statistics.stdev(intervals) if len(intervals) > 1 else 0

            # Frequency Detection (Monthly: 25-35 days, Weekly: 6-8 days)
            frequency = None
            if 25 <= avg_interval <= 35 and std_dev < 5:
                frequency = "MONTHLY"
            elif 6 <= avg_interval <= 8 and std_dev < 2:
                frequency = "WEEKLY"

            if frequency:
                # Check if already tracked
                existing = db.query(models.RecurringTransaction).filter(
                    models.RecurringTransaction.tenant_id == tenant_id,
                    models.RecurringTransaction.name.ilike(f"%{merchant}%")
                ).first()
                
                if existing: continue

                # Calculate median amount
                amounts = [t.amount for t in txns]
                median_amount = statistics.median(amounts)

                suggestions.append(schemas.RecurringSuggestion(
                    name=merchant.title(),
                    amount=median_amount,
                    frequency=frequency,
                    category=txns[-1].category,
                    account_id=txns[-1].account_id,
                    confidence=min(0.9, 0.5 + (len(txns) * 0.1)),
                    reason=f"Detected {len(txns)} transactions matching every {frequency.lower().replace('ly', '')}",
                    last_date=txns[-1].date
                ))

        return sorted(suggestions, key=lambda x: x.confidence, reverse=True)
