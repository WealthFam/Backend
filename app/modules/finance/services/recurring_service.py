from typing import List, Optional
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session
from backend.app.modules.finance import models, schemas
from backend.app.core import timezone
import statistics
import re
from datetime import datetime

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
                exclude_from_reports=item.exclude_from_reports,
                latitude=item.latitude,
                longitude=item.longitude
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
                    import logging
                    logging.error(f"Error creating recurring transaction {item.id}: {e}")
            except Exception as e:
                import logging
                logging.error(f"Unexpected error in recurring txn {item.id}: {e}")
                # Don't crash the whole batch
                pass
            
            # Update Next Run Date
            next_date = item.next_run_date
            if item.frequency == models.Frequency.DAILY:
                next_date += relativedelta(days=1)
            elif item.frequency == models.Frequency.WEEKLY:
                next_date += relativedelta(weeks=1)
            elif item.frequency == models.Frequency.BI_WEEKLY: # Changed to use enum member
                next_date += relativedelta(weeks=2)
            elif item.frequency == models.Frequency.MONTHLY:
                next_date += relativedelta(months=1)
            elif item.frequency == models.Frequency.QUARTERLY: # Changed to use enum member
                next_date += relativedelta(months=3)
            elif item.frequency == models.Frequency.YEARLY:
                next_date += relativedelta(years=1)
            
            item.next_run_date = next_date
            
        db.commit()
        return count

    @staticmethod
    def ignore_suggestion(db: Session, pattern: str, tenant_id: str) -> bool:
        """
        Adds a pattern to the ignored suggestions list.
        """
        try:
            db_ignore = models.IgnoredRecurringPattern(
                pattern=pattern.upper(),
                tenant_id=tenant_id
            )
            db.add(db_ignore)
            db.commit()
            return True
        except Exception as e:
            import logging
            logging.error(f"Error ignoring suggestion: {e}")
            db.rollback()
            return False

    @staticmethod
    def get_recurring_suggestions(db: Session, tenant_id: str) -> List[schemas.RecurringSuggestion]:
        """
        Analyzes transaction history to find complex recurring patterns.
        Supports Weekly, Bi-Weekly, Monthly, Quarterly, and Yearly.
        """
        from collections import defaultdict
        from datetime import datetime

        # 1. Fetch Ignored Patterns
        ignored_patterns = db.query(models.IgnoredRecurringPattern).filter(
            models.IgnoredRecurringPattern.tenant_id == tenant_id
        ).all()
        ignored_set = {p.pattern.upper() for p in ignored_patterns}

        # 2. Fetch recent debit transactions (last 12 months)
        lookback_date = timezone.utcnow() - relativedelta(months=12)
        transactions = db.query(models.Transaction).filter(
            models.Transaction.tenant_id == tenant_id,
            models.Transaction.type == models.TransactionType.DEBIT,
            models.Transaction.date >= lookback_date,
            models.Transaction.is_transfer == False,
            models.Transaction.is_emi == False
        ).order_by(models.Transaction.date.desc()).all()

        # 3. Normalization Helper
        def normalize_merchant(name: str) -> str:
            if not name: return ""
            # Remove trailing numbers/dates
            name = re.sub(r'\d+$', '', name)
            # Remove common domain suffixes
            name = re.sub(r'\.(com|in|org|net)$', '', name, flags=re.IGNORECASE)
            return name.strip().upper()

        # 4. Group by Merchant AND Amount (to handle multiple subscriptions/outliers)
        # We allow a small 2% buffer in amount for "same amount" grouping
        groups = defaultdict(list)
        for t in transactions:
            raw_name = t.recipient or t.description
            if not raw_name: continue
            norm_name = normalize_merchant(raw_name)
            
            if norm_name in ignored_set or len(norm_name) < 3:
                continue
            
            # Use rounded amount as partial key to separate distinct subscriptions
            amt_key = round(float(t.amount), -1) # Round to nearest 10 for grouping
            groups[(norm_name, amt_key)].append(t)

        suggestions = []
        
        freq_profiles = [
            ("WEEKLY", 7, 2),
            ("BI-WEEKLY", 14, 3),
            ("MONTHLY", 30, 7),
            ("QUARTERLY", 91, 10),
            ("YEARLY", 365, 20)
        ]

        # 5. Analyze each (Merchant, Amount) group
        for (merchant, _), txns in groups.items():
            if len(txns) < 2: continue 

            txns.sort(key=lambda x: x.date)
            intervals = []
            days_of_month = []
            days_of_week = []
            months = []
            
            for i in range(1, len(txns)):
                intervals.append((txns[i].date - txns[i-1].date).days)
            
            for t in txns:
                days_of_month.append(t.date.day)
                days_of_week.append(t.date.weekday())
                months.append(t.date.month)

            if not intervals: continue

            avg_interval = sum(intervals) / len(intervals)
            # Use median for better outlier resistance
            median_interval = sorted(intervals)[len(intervals)//2]
            
            # Stability Metrics
            dom_std = statistics.stdev(days_of_month) if len(days_of_month) > 1 else 0
            dow_std = statistics.stdev(days_of_week) if len(days_of_week) > 1 else 0
            month_std = statistics.stdev(months) if len(months) > 1 else 0

            detected_freq = None
            matched_target_days = 0
            
            for name, target_days, tolerance in freq_profiles:
                min_points = 3 if name in ["WEEKLY", "MONTHLY", "BI-WEEKLY"] else 2
                if len(txns) < min_points: continue

                # Distance check
                if abs(median_interval - target_days) <= tolerance:
                    is_stable = False
                    
                    # Frequency-specific stability signals
                    if name == "MONTHLY":
                        # Monthly is stable if either avg interval is ~30 OR day of month is consistent
                        if dom_std <= 3 or abs(avg_interval - 30) <= 4:
                            is_stable = True
                    elif name == "WEEKLY" or name == "BI-WEEKLY":
                        # Weekly is stable if day of week is consistent
                        if dow_std <= 1:
                            is_stable = True
                    elif name == "YEARLY":
                        # Yearly is stable if month and day are consistent
                        if dom_std <= 5 and month_std <= 0.5: # Needs same month
                            is_stable = True
                    else:
                        # General fallback for others (Quarterly)
                        if abs(avg_interval - target_days) <= (tolerance / 2):
                            is_stable = True
                            
                    if is_stable:
                        detected_freq = name
                        matched_target_days = target_days
                        break

            if detected_freq:
                # Deduplication
                existing = db.query(models.RecurringTransaction).filter(
                    models.RecurringTransaction.tenant_id == tenant_id,
                    models.RecurringTransaction.name.ilike(f"%{merchant}%")
                ).first()
                if existing: continue

                avg_amount = sum(t.amount for t in txns) / len(txns)
                
                # Confidence Calculation
                # Base confidence on frequency + occurrences
                confidence = 0.5 + (min(len(txns), 6) * 0.05)
                
                # Bonus for High Stability
                if detected_freq == "MONTHLY" and dom_std <= 1.5:
                    confidence += 0.15
                if (detected_freq == "WEEKLY" or detected_freq == "BI-WEEKLY") and dow_std < 0.5:
                    confidence += 0.15
                if detected_freq == "YEARLY" and dom_std <= 2:
                    confidence += 0.2

                suggestions.append(schemas.RecurringSuggestion(
                    name=merchant.title(),
                    amount=avg_amount,
                    frequency=detected_freq,
                    category=txns[-1].category,
                    account_id=txns[-1].account_id,
                    confidence=min(0.98, confidence),
                    reason=f"Consistent {detected_freq.lower()} pattern found across {len(txns)} payments.",
                    last_date=txns[-1].date,
                    pattern=merchant,
                    detected_count=len(txns)
                ))

        return sorted(suggestions, key=lambda x: x.confidence, reverse=True)
