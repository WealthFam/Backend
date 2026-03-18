import json
import logging
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

logger = logging.getLogger(__name__)

from backend.app.core.database import db_write_lock
from backend.app.core.timezone import ensure_utc
from backend.app.modules.finance import models, schemas
from backend.app.modules.finance.models import TransactionType
from backend.app.modules.finance.services.category_service import CategoryService
from backend.app.modules.finance.services.transfer_service import TransferService
from backend.app.modules.ingestion import models as ingestion_models
from backend.app.modules.ingestion.deduplicator import TransactionDeduplicator

class TransactionService:
    @staticmethod
    def create_transaction(db: Session, transaction: schemas.TransactionCreate, tenant_id: str, exclude_pending_id: Optional[str] = None, update_balance: bool = True):
        with db_write_lock:
            # 1. Unified Deduplication Check (Ref ID, Hash-Fallback, and Fields)
            
            # Skip strict deduplication for MANUAL entries to allow user intent
            is_dup = False
            reason = None
            existing_id = None
            
            if getattr(transaction, 'source', 'MANUAL') != 'MANUAL':
                is_dup, reason, existing_id = TransactionDeduplicator.check_raw_duplicate(
                    db, tenant_id, str(transaction.account_id), transaction.amount, transaction.date, 
                    transaction.description, transaction.recipient, transaction.external_id,
                    exclude_pending_id=exclude_pending_id
                )
            
            if is_dup:
                # If it found a match in confirmed transactions, return it
                # We check the confirmed table specifically here to be sure
                existing = db.query(models.Transaction).filter(models.Transaction.id == existing_id).first()
                if existing: return existing
                
                # If it was in pending/triage, the deduplicator returns it, but create_transaction 
                # should probably still proceed or throw if it's strictly enforced.
                # In our system, manual creation/import should skip if already in triage too.
                # For now, let's treat it as a skip (return None or raise?) 
                # But the service signature returns models.Transaction.
                # Easiest: return None or raise. Usually create_transaction should be idempotent.
                # If it's a confirmed duplicate in another table, we return it to represent "creation was handled"
                # If it's simply "triage", we skip creation in confirmed.
                return None
    
            data = transaction.model_dump()
            data['tenant_id'] = tenant_id
            
            # Use UUID if not provided (though models usually handle this, explicit is safer for deduplication sync)
            if not data.get('id'):
                import uuid
                data['id'] = str(uuid.uuid4())
    
            # Content Hash for weak deduplication
            if not data.get('content_hash'):
                from backend.app.modules.ingestion.deduplicator import TransactionDeduplicator
                data['content_hash'] = TransactionDeduplicator.generate_hash(
                    tenant_id, str(data['account_id']), data['date'], data['amount'], 
                    data['description'], data['recipient']
                )
    
            db_transaction = models.Transaction(**data)
            db.add(db_transaction)
            
            # 2. Update Account Balance
            if update_balance:
                db_account = db.query(models.Account).filter(
                    models.Account.id == transaction.account_id,
                    models.Account.tenant_id == tenant_id
                ).first()
                
                if db_account:
                    from backend.app.core import timezone
                    anchor_date = timezone.ensure_utc(db_account.last_synced_at)
                    txn_date = timezone.ensure_utc(db_transaction.date)
                    
                    # Only affect balance if transaction is NEWER than the last sync anchor
                    if not anchor_date or txn_date > anchor_date:
                        # Transaction amount is already signed (e.g. -500 for debit)
                        # For LOAN/CREDIT accounts, a debit (-500) INCREASES the positive balance (debt)
                        # For BANK accounts, a debit (-500) DECREASES the positive balance
                        
                        balance_change = 0
                        if db_account.type in [models.AccountType.LOAN, models.AccountType.CREDIT_CARD]:
                            # Debt increase = -(-500) = +500
                            balance_change = -db_transaction.amount
                        else:
                            # Cash decrease = +(-500) = -500
                            balance_change = db_transaction.amount
                        
                        # Atomic balance update to prevent race conditions
                        if balance_change != 0:
                            db.query(models.Account).filter(models.Account.id == db_account.id).update({
                                "balance": models.Account.balance + balance_change
                            })
            
            db.commit()
            db.refresh(db_transaction)
            
            # 3. Trigger Real-time Notification
            try:
                from backend.app.modules.notifications.services import NotificationService
                # Fetch fresh account name for notification
                db_account = db.query(models.Account).filter(models.Account.id == db_transaction.account_id).first()
                if db_account:
                    NotificationService.notify_transaction(
                        db, 
                        tenant_id, 
                        db_transaction.amount, 
                        db_transaction.description or db_transaction.recipient, 
                        db_account.name,
                        user_id=db_account.owner_id
                    )
            except Exception as e:
                logger.error(f"Failed to trigger transaction notification: {e}")
    
            return db_transaction

    @staticmethod
    def get_transactions(
        db: Session, 
        tenant_id: str, 
        account_id: Optional[str] = None, 
        skip: int = 0,
        limit: int = 50,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        search: Optional[str] = None,
        category: Optional[str] = None,
        user_role: str = "ADULT",
        user_id: Optional[str] = None,
        exclude_from_reports: bool = False,
        exclude_transfers: bool = False,
        sort_by: str = "date",
        sort_order: str = "desc"
    ) -> List[models.Transaction]:
        if end_date:
            end_date = ensure_utc(end_date).replace(hour=23, minute=59, second=59, microsecond=999999)

        query = db.query(models.Transaction).options(
            joinedload(models.Transaction.account)
        ).filter(models.Transaction.tenant_id == tenant_id)
        
        if user_role == "CHILD":
            query = query.join(models.Account, models.Transaction.account_id == models.Account.id)\
                         .filter(models.Account.type.notin_(["INVESTMENT", "CREDIT"]))

        if account_id:
            query = query.filter(models.Transaction.account_id == account_id)
        if start_date:
            query = query.filter(models.Transaction.date >= ensure_utc(start_date))

        if end_date:
            query = query.filter(models.Transaction.date <= end_date)
        
        if search:
            search_pattern = f"%{search}%"
            from sqlalchemy import or_
            query = query.filter(or_(
                models.Transaction.description.ilike(search_pattern),
                models.Transaction.recipient.ilike(search_pattern)
            ))
            
        if category:
            # Hierarchical Category Filtering
            from backend.app.modules.finance.models import Category
            sub_category_names = []
            
            if category == "Uncategorized":
                query = query.filter(or_(models.Transaction.category == None, models.Transaction.category == "Uncategorized"))
            else:
                # Check if this is a parent category
                parent_cat = db.query(Category).filter(
                    Category.tenant_id == tenant_id,
                    Category.name == category,
                    Category.parent_id == None
                ).first()
                
                
                if parent_cat:
                    # Find all subcategories
                    subs = db.query(Category).filter(Category.parent_id == parent_cat.id).all()
                    sub_category_names = [s.name for s in subs]
                
                if sub_category_names:
                    filter_list = [category] + sub_category_names
                    query = query.filter(models.Transaction.category.in_(filter_list))
                else:
                    query = query.filter(models.Transaction.category == category)

        if exclude_from_reports:
            query = query.filter(models.Transaction.exclude_from_reports == False)
        if exclude_transfers:
            query = query.filter(models.Transaction.is_transfer == False)

        if user_id:
            # Filter by account ownership: show user's accounts OR shared accounts
            from sqlalchemy import or_
            query = query.outerjoin(models.Account, models.Transaction.account_id == models.Account.id)\
                         .filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))
            
        sort_column = models.Transaction.date
        if sort_by == "amount":
            sort_column = models.Transaction.amount
        elif sort_by == "description":
            sort_column = models.Transaction.description
        elif sort_by == "recipient":
            sort_column = models.Transaction.recipient
        elif sort_by == "category":
            sort_column = models.Transaction.category

        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        return query.offset(skip).limit(limit).all()

    @staticmethod
    def get_vendor_stats(db: Session, tenant_id: str, vendor_name: str, user_id: Optional[str] = None, skip: int = 0, limit: int = 3) -> dict:
        search_pattern = f"%{vendor_name}%"
        from sqlalchemy import or_, func, desc
        from dateutil.relativedelta import relativedelta
        from backend.app.core import timezone
        now = timezone.utcnow()
        six_months_ago = now - relativedelta(months=6)


        query = db.query(models.Transaction).filter(
            models.Transaction.tenant_id == tenant_id,
            models.Transaction.exclude_from_reports == False,
            models.Transaction.is_transfer == False,
            or_(
                models.Transaction.description.ilike(search_pattern),
                models.Transaction.recipient.ilike(search_pattern)
            )
        )
        if user_id:
            query = query.outerjoin(models.Account, models.Transaction.account_id == models.Account.id)\
                         .filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))

        # Total count for pagination
        total_count = query.count()
        
        # Stats are based on all transactions for this vendor
        all_txns = query.all()
        
        total_spent = sum(abs(t.amount) for t in all_txns if t.amount < 0)
        total_income = sum(t.amount for t in all_txns if t.amount > 0)
        
        debit_count = sum(1 for t in all_txns if t.amount < 0)
        avg_txn = (total_spent / debit_count) if debit_count > 0 else 0

        # Group by month for chart
        monthly_map = {}
        for i in range(6):
            dt = now - relativedelta(months=i)
            key = f"{dt.year}-{dt.month:02d}"
            monthly_map[key] = 0.0
            
        for t in all_txns:
            if t.date >= six_months_ago and t.amount < 0:
                key = f"{t.date.year}-{t.date.month:02d}"
                if key in monthly_map:
                    monthly_map[key] += float(abs(t.amount))
                    
        chart_data = [{"month": k, "amount": v} for k, v in reversed(monthly_map.items())]

        # Paginated recent transactions
        recent_txns = query.order_by(desc(models.Transaction.date)).offset(skip).limit(limit).all()

        return {
            "vendor_name": vendor_name,
            "total_spent": total_spent,
            "total_income": total_income,
            "transaction_count": total_count,
            "average_transaction": avg_txn,
            "chart_data": chart_data,
            "recent_transactions": [{"id": t.id, "date": t.date.isoformat(), "amount": t.amount, "description": t.description, "category": t.category} for t in recent_txns]
        }

    @staticmethod
    def count_transactions(
        db: Session, 
        tenant_id: str, 
        account_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        search: Optional[str] = None,
        category: Optional[str] = None,
        user_role: str = "ADULT",
        user_id: Optional[str] = None,
        exclude_from_reports: bool = False,
        exclude_transfers: bool = False
    ) -> int:
        if end_date:
            end_date = ensure_utc(end_date).replace(hour=23, minute=59, second=59, microsecond=999999)

        if user_id in [None, "null", "undefined", ""]:
            user_id = None
        if category in [None, "null", "undefined", "", "OVERALL"]:
            category = None
            
        query = db.query(models.Transaction).filter(models.Transaction.tenant_id == tenant_id)

        if user_role == "CHILD":
            query = query.join(models.Account, models.Transaction.account_id == models.Account.id)\
                         .filter(models.Account.type.notin_(["INVESTMENT", "CREDIT"]))

        if account_id:
            query = query.filter(models.Transaction.account_id == account_id)
        
        if user_id:
            # Filter by account ownership: show user's accounts OR shared accounts
            from sqlalchemy import or_
            query = query.outerjoin(models.Account, models.Transaction.account_id == models.Account.id)\
                         .filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))

        if start_date:
            query = query.filter(models.Transaction.date >= ensure_utc(start_date))

        if end_date:
            query = query.filter(models.Transaction.date <= end_date)
            
        if search:
            search_pattern = f"%{search}%"
            from sqlalchemy import or_
            query = query.filter(or_(
                models.Transaction.description.ilike(search_pattern),
                models.Transaction.recipient.ilike(search_pattern)
            ))
            
        if category:
            # Hierarchical Category Filtering
            from backend.app.modules.finance.models import Category
            sub_category_names = []
            
            if category == "Uncategorized":
                query = query.filter(or_(models.Transaction.category == None, models.Transaction.category == "Uncategorized"))
            else:
                parent_cat = db.query(Category).filter(
                    Category.tenant_id == tenant_id,
                    Category.name == category,
                    Category.parent_id == None
                ).first()
                
                if parent_cat:
                    subs = db.query(Category).filter(Category.parent_id == parent_cat.id).all()
                    sub_category_names = [s.name for s in subs]
                
                if sub_category_names:
                    query = query.filter(models.Transaction.category.in_([category] + sub_category_names))
                else:
                    query = query.filter(models.Transaction.category == category)
            
        if exclude_from_reports:
            query = query.filter(models.Transaction.exclude_from_reports == False)
        if exclude_transfers:
            query = query.filter(models.Transaction.is_transfer == False)
            
        return query.count()

    @staticmethod
    def bulk_delete_transactions(db: Session, transaction_ids: List[str], tenant_id: str) -> int:
        if not transaction_ids: return 0
        with db_write_lock:
            try:
                # 1. Fetch transactions to be deleted (we need details for balance update)
                txns = db.query(models.Transaction).filter(
                    models.Transaction.id.in_(transaction_ids),
                    models.Transaction.tenant_id == tenant_id
                ).all()
                
                if not txns: return 0
                
                # 2. Group by account to minimize DB lookups
                from collections import defaultdict
                txns_by_account = defaultdict(list)
                for t in txns:
                    txns_by_account[t.account_id].append(t)
                    
                # 3. Update balances
                for acc_id, account_txns in txns_by_account.items():
                    account = db.query(models.Account).filter(models.Account.id == acc_id).first()
                    if not account: continue
                    
                    balance_change = 0
                    from backend.app.core import timezone
                    anchor_date = timezone.ensure_utc(account.last_synced_at)
                    
                    for t in account_txns:
                        # Only revert balance if txn is NEWER than anchor.
                        # If older/equal, it's baked into the anchor snapshot.
                        txn_date = timezone.ensure_utc(t.date)
                        if not anchor_date or txn_date > anchor_date:
                            # Revert logic:
                            # Create (Loan): bal = bal - amt  => Undo: bal = bal + amt
                            # Create (Bank): bal = bal + amt  => Undo: bal = bal - amt
                            if account.type in [models.AccountType.LOAN, models.AccountType.CREDIT_CARD]:
                                balance_change += t.amount
                            else:
                                balance_change -= t.amount
    
                    
                    if balance_change != 0:
                        # Atomic balance update to prevent race conditions
                        db.query(models.Account).filter(models.Account.id == acc_id).update({
                            "balance": models.Account.balance + balance_change
                        })
                
                # 4. Perform Delete
                # Since we fetched objects, we could delete them directly or use bulk delete.
                # Bulk delete is still efficient for the deletion part.
                count = db.query(models.Transaction).filter(
                    models.Transaction.id.in_(transaction_ids),
                    models.Transaction.tenant_id == tenant_id
                ).delete(synchronize_session=False)
                
                db.commit()
                return count
            except Exception as e:
                db.rollback()
                raise e

    @staticmethod
    def update_transaction(db: Session, txn_id: str, txn_update: schemas.TransactionUpdate, tenant_id: str) -> Optional[models.Transaction]:
        with db_write_lock:
            db_txn = db.query(models.Transaction).filter(
                models.Transaction.id == txn_id,
                models.Transaction.tenant_id == tenant_id
            ).first()
        
            if not db_txn:
                return None
                
            # Snapshot old state for balance adjustment
            old_amount = db_txn.amount
            old_date = db_txn.date
            old_account_id = db_txn.account_id
            
            update_data = txn_update.model_dump(exclude_unset=True)
            
            # --- Transfer logic remains same ---
            is_transfer_update = update_data.get('is_transfer')
            to_account_id = update_data.get('to_account_id')
            
            if is_transfer_update is True:
                db_txn.is_transfer = True
                db_txn.exclude_from_reports = True
                
                if update_data.get('linked_transaction_id'):
                    if db_txn.linked_transaction_id:
                         old_linked = db.query(models.Transaction).filter(models.Transaction.id == db_txn.linked_transaction_id).first()
                         if old_linked:
                            old_linked.linked_transaction_id = None
                            db.add(old_linked)
    
                    target_id = update_data['linked_transaction_id']
                    target_txn = db.query(models.Transaction).filter(models.Transaction.id == target_id).first()
                    
                    if target_txn:
                        db_txn.linked_transaction_id = target_txn.id
                        target_txn.linked_transaction_id = db_txn.id
                        target_txn.is_transfer = True
                        target_txn.category = "Transfer"
                        target_txn.exclude_from_reports = True 
                        db.add(target_txn)
    
                elif to_account_id:
                    if db_txn.linked_transaction_id:
                         old_linked = db.query(models.Transaction).filter(models.Transaction.id == db_txn.linked_transaction_id).first()
                         if old_linked: db.delete(old_linked)
                    
                    target_txn = models.Transaction(
                        id=str(uuid.uuid4()),
                        tenant_id=tenant_id,
                        account_id=to_account_id,
                        amount=-db_txn.amount if 'amount' not in update_data else -update_data['amount'],
                        date=db_txn.date if 'date' not in update_data else update_data['date'],
                        description=f"Transfer from {db_txn.account_id} (Linked)",
                        recipient=db_txn.recipient,
                        category="Transfer",
                        type=TransactionType.CREDIT if (db_txn.amount < 0) else TransactionType.DEBIT,
                        is_transfer=True,
                        source=db_txn.source,
                        linked_transaction_id=db_txn.id,
                        exclude_from_reports=True
                    )
                    db.add(target_txn)
                    db_txn.linked_transaction_id = target_txn.id
                    db_txn.category = "Transfer"
                    update_data['category'] = "Transfer"
    
            elif is_transfer_update is False:
                db_txn.is_transfer = False
                if db_txn.linked_transaction_id:
                    linked = db.query(models.Transaction).filter(models.Transaction.id == db_txn.linked_transaction_id).first()
                    if linked:
                        linked.linked_transaction_id = None
                        linked.is_transfer = False 
                        db.add(linked)
    
                    db_txn.linked_transaction_id = None
            
            # Apply updates to db_txn
            for key, value in update_data.items():
                if key in ['is_transfer', 'to_account_id']: continue
                if key == 'tags' and value is not None:
                    setattr(db_txn, key, json.dumps(value))
                elif key in ['linked_transaction_id', 'expense_group_id', 'loan_id'] and value == "":
                    setattr(db_txn, key, None)
                elif key == 'account_id' and value:
                    db_txn.account_id = str(value)
                else:
                    setattr(db_txn, key, value)
            
            # Recalculate type based on final amount
            db_txn.type = models.TransactionType.DEBIT if db_txn.amount < 0 else models.TransactionType.CREDIT

            # Account for balance changes if amount, date, or account changed
            from backend.app.core import timezone
            has_important_change = (
                'amount' in update_data or 
                'date' in update_data or 
                'account_id' in update_data
            )
            
            if has_important_change:
                # 1. Revert Old Balance Contribution
                old_acc = db.query(models.Account).filter(models.Account.id == old_account_id).first()
                if old_acc:
                    old_anchor = timezone.ensure_utc(old_acc.last_synced_at)
                    old_txn_date = timezone.ensure_utc(old_date)
                    
                    if not old_anchor or old_txn_date > old_anchor:
                        old_revert_change = 0
                        if old_acc.type in [models.AccountType.LOAN, models.AccountType.CREDIT_CARD]:
                            old_revert_change = old_amount
                        else:
                            old_revert_change = -old_amount
                        
                        if old_revert_change != 0:
                            db.query(models.Account).filter(models.Account.id == old_account_id).update({
                                "balance": models.Account.balance + old_revert_change
                            })
                
                # 2. Apply New Balance Contribution
                new_account_id = db_txn.account_id
                new_amount = db_txn.amount
                new_date = db_txn.date
                
                new_acc_exists = db.query(models.Account).filter(models.Account.id == new_account_id).first()
                if new_acc_exists:
                    new_anchor = timezone.ensure_utc(new_acc_exists.last_synced_at)
                    new_txn_date = timezone.ensure_utc(new_date)
                    
                    if not new_anchor or new_txn_date > new_anchor:
                        new_balance_change = 0
                        if new_acc_exists.type in [models.AccountType.LOAN, models.AccountType.CREDIT_CARD]:
                            new_balance_change = -new_amount
                        else:
                            new_balance_change = new_amount
                        
                        if new_balance_change != 0:
                            db.query(models.Account).filter(models.Account.id == new_account_id).update({
                                "balance": models.Account.balance + new_balance_change
                            })
    
            # -------------------------------
                    
            db.commit()
            db.refresh(db_txn)
            return db_txn

    @staticmethod
    def get_suggested_category(db: Session, tenant_id: str, description: Optional[str], recipient: Optional[str]) -> str:
        if not description and not recipient:
            return "Uncategorized"
            
        rules = db.query(models.CategoryRule).filter(models.CategoryRule.tenant_id == tenant_id).order_by(models.CategoryRule.priority.desc()).all()
        
        desc_lower = (description or "").lower()
        recipient_lower = (recipient or "").lower()
        
        for rule in rules:
            try:
                keywords = json.loads(rule.keywords)
                if any(k.lower() in desc_lower or k.lower() in recipient_lower for k in keywords):
                    return rule.category
            except:
                continue
        return "Uncategorized"

    # --- Triage Functions ---
    @staticmethod
    def get_pending_transactions(
        db: Session, 
        tenant_id: str, 
        skip: int = 0, 
        limit: int = 50, 
        sort_by: str = "date", 
        sort_order: str = "desc",
        search: Optional[str] = None,
        source: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        if user_id in [None, "null", "undefined", ""]:
            user_id = None
        query = db.query(ingestion_models.PendingTransaction).options(
            joinedload(ingestion_models.PendingTransaction.account)
        ).filter(
            ingestion_models.PendingTransaction.tenant_id == tenant_id
        )

        if user_id:
            # Join with Account to filter by owner
            from backend.app.modules.finance import models as finance_models
            from sqlalchemy import or_
            query = query.outerjoin(finance_models.Account, ingestion_models.PendingTransaction.account_id == finance_models.Account.id)\
                         .filter(or_(finance_models.Account.owner_id == user_id, finance_models.Account.owner_id == None))
        
        # Filter by source (SMS, EMAIL, etc.)
        if source:
            query = query.filter(ingestion_models.PendingTransaction.source == source)
        
        # Filter by search query (description, recipient, amount, ID)
        if search:
            from sqlalchemy import or_, cast, String
            search_pattern = f"%{search}%"
            query = query.filter(or_(
                ingestion_models.PendingTransaction.description.ilike(search_pattern),
                ingestion_models.PendingTransaction.recipient.ilike(search_pattern),
                ingestion_models.PendingTransaction.id.ilike(search_pattern),
                cast(ingestion_models.PendingTransaction.amount, String).like(search_pattern)
            ))
        
        total = query.count()
        
        sort_column = ingestion_models.PendingTransaction.created_at
        if sort_by == "amount":
            sort_column = ingestion_models.PendingTransaction.amount
        elif sort_by == "description":
            sort_column = ingestion_models.PendingTransaction.description
        elif sort_by == "date":
            sort_column = ingestion_models.PendingTransaction.date
        
        if sort_order == "asc":
            query = query.order_by(sort_column.asc(), ingestion_models.PendingTransaction.created_at.asc())
        else:
            query = query.order_by(sort_column.desc(), ingestion_models.PendingTransaction.created_at.desc())
            
        return query.offset(skip).limit(limit).all(), total

    @staticmethod
    def approve_pending_transaction(
        db: Session, 
        pending_id: str, 
        tenant_id: str, 
        category_override: Optional[str] = None,
        is_transfer_override: bool = False,
        to_account_id_override: Optional[str] = None,
        exclude_from_reports_override: Optional[bool] = None,
        create_rule: bool = False,
        account_id_override: Optional[str] = None
    ):
        pending = db.query(ingestion_models.PendingTransaction).filter(
            ingestion_models.PendingTransaction.id == pending_id,
            ingestion_models.PendingTransaction.tenant_id == tenant_id
        ).first()
        if not pending: return None
        
        final_is_transfer = is_transfer_override or pending.is_transfer
        final_to_account_id = to_account_id_override or pending.to_account_id
        final_category = category_override or pending.category or "Uncategorized"
        final_exclude = exclude_from_reports_override if exclude_from_reports_override is not None else pending.exclude_from_reports
        final_account_id = account_id_override or pending.account_id
        
        # Sync exclude if it was forced to transfer here
        if is_transfer_override:
            final_exclude = True
        
        if create_rule and pending.description:
            rule_create = schemas.CategoryRuleCreate(
                name=f"Rule for {pending.description[:20]}...",
                category=final_category,
                keywords=[pending.description],
                is_transfer=final_is_transfer,
                to_account_id=final_to_account_id,
                priority=10
            )
            CategoryService.create_category_rule(db, rule_create, tenant_id)

        txn_create = schemas.TransactionCreate(
            account_id=final_account_id,
            amount=pending.amount,
            date=pending.date,
            description=pending.description,
            recipient=pending.recipient,
            category=final_category,
            external_id=pending.external_id,
            source=pending.source,
            is_transfer=final_is_transfer,
            to_account_id=final_to_account_id,
            tags=[],
            exclude_from_reports=final_exclude,
            latitude=pending.latitude,
            longitude=pending.longitude,
            location_name=pending.location_name
        )
        
        if txn_create.is_transfer and txn_create.to_account_id:
            pending.is_transfer = final_is_transfer
            pending.to_account_id = final_to_account_id
            pending.exclude_from_reports = final_exclude
            real_txn = TransferService.approve_transfer(db, pending, tenant_id)
        else:
            real_txn = TransactionService.create_transaction(
                db, txn_create, tenant_id, 
                exclude_pending_id=pending_id,
                update_balance=not getattr(pending, 'balance_is_synced', False)
            )

        db.delete(pending)
        db.commit()
        return real_txn

    @staticmethod
    def reject_pending_transaction(db: Session, pending_id: str, tenant_id: str, create_ignore_rule: bool = False):
        pending = db.query(ingestion_models.PendingTransaction).filter(
            ingestion_models.PendingTransaction.id == pending_id,
            ingestion_models.PendingTransaction.tenant_id == tenant_id
        ).first()
        if not pending: return False
        
        if create_ignore_rule:
            pattern = pending.recipient or pending.description
            if pattern:
                # Check if already exists
                existing = db.query(ingestion_models.IgnoredPattern).filter(
                    ingestion_models.IgnoredPattern.tenant_id == tenant_id,
                    ingestion_models.IgnoredPattern.pattern == pattern
                ).first()
                if not existing:
                    new_ignore = ingestion_models.IgnoredPattern(
                        tenant_id=tenant_id,
                        pattern=pattern,
                        source=pending.source
                    )
                    db.add(new_ignore)

        db.delete(pending)
        db.commit()
        return True

    @staticmethod
    def bulk_reject_pending_transactions(db: Session, pending_ids: List[str], tenant_id: str, create_ignore_rules: bool = False):
        if not pending_ids: return 0
        
        if create_ignore_rules:
            pendings = db.query(ingestion_models.PendingTransaction).filter(
                ingestion_models.PendingTransaction.id.in_(pending_ids),
                ingestion_models.PendingTransaction.tenant_id == tenant_id
            ).all()
            for p in pendings:
                pattern = p.recipient or p.description
                if pattern:
                    existing = db.query(ingestion_models.IgnoredPattern).filter(
                        ingestion_models.IgnoredPattern.tenant_id == tenant_id,
                        ingestion_models.IgnoredPattern.pattern == pattern
                    ).first()
                    if not existing:
                        new_ignore = ingestion_models.IgnoredPattern(
                            tenant_id=tenant_id,
                            pattern=pattern,
                            source=p.source
                        )
                        db.add(new_ignore)
        
        count = db.query(ingestion_models.PendingTransaction).filter(
            ingestion_models.PendingTransaction.id.in_(pending_ids),
            ingestion_models.PendingTransaction.tenant_id == tenant_id
        ).delete(synchronize_session=False)
        db.commit()
        return count

    @staticmethod
    def batch_update_category_and_create_rule(
        db: Session, 
        txn_id: str, 
        category: str, 
        tenant_id: str,
        create_rule: bool = False,
        apply_to_similar: bool = False,
        exclude_from_reports: bool = False
    ) -> dict:
        db_txn = db.query(models.Transaction).filter(
            models.Transaction.id == txn_id,
            models.Transaction.tenant_id == tenant_id
        ).first()
        
        if not db_txn:
            return {"success": False, "message": "Transaction not found"}
            
        old_category = db_txn.category
        db_txn.category = category
        if exclude_from_reports:
            db_txn.exclude_from_reports = True
        db.add(db_txn)
        
        affected_count = 1
        rule_created = False
        
        pattern = db_txn.recipient or db_txn.description
        if not pattern:
            db.commit()
            return {"success": True, "affected": affected_count, "rule_created": False}

        if create_rule:
            existing_rule = db.query(models.CategoryRule).filter(
                models.CategoryRule.tenant_id == tenant_id,
                models.CategoryRule.name == f"Auto: {pattern}"
            ).first()
            
            if not existing_rule:
                new_rule = models.CategoryRule(
                    tenant_id=tenant_id,
                    name=f"Auto: {pattern}",
                    category=category,
                    keywords=json.dumps([pattern]),
                    priority=1,
                    exclude_from_reports=exclude_from_reports
                )
                db.add(new_rule)
                rule_created = True
            else:
                # Update existing rule to reflect new decision
                existing_rule.category = category
                existing_rule.exclude_from_reports = exclude_from_reports
                db.add(existing_rule)
                rule_created = True

        if apply_to_similar:
            from sqlalchemy import or_
            query = db.query(models.Transaction).filter(
                models.Transaction.tenant_id == tenant_id,
                models.Transaction.id != txn_id,
                (models.Transaction.category == "Uncategorized") | (models.Transaction.category == None)
            )
            
            search_pattern = f"%{pattern}%"
            query = query.filter(or_(
                models.Transaction.description.ilike(search_pattern),
                models.Transaction.recipient.ilike(search_pattern)
            ))
                
            similar_txns = query.all()
            for st in similar_txns:
                st.category = category
                if exclude_from_reports:
                    st.exclude_from_reports = True
                db.add(st)
                affected_count += 1

        db.commit()
        return {
            "success": True, 
            "affected": affected_count, 
            "rule_created": rule_created,
            "pattern": pattern
        }

    @staticmethod
    def apply_rule_retrospectively(db: Session, rule_id: str, tenant_id: str, override: bool = False) -> dict:
        rule = db.query(models.CategoryRule).filter(
            models.CategoryRule.id == rule_id,
            models.CategoryRule.tenant_id == tenant_id
        ).first()
        
        if not rule:
            return {"success": False, "message": "Rule not found"}
        
        keywords = json.loads(rule.keywords)
        if not keywords:
            return {"success": True, "affected": 0}
            
        filters = []
        for k in keywords:
            pattern = f"%{k}%"
            filters.append(or_(
                models.Transaction.description.ilike(pattern),
                models.Transaction.recipient.ilike(pattern)
            ))
            
        # 1. Update Confirmed Transactions
        query = db.query(models.Transaction).filter(models.Transaction.tenant_id == tenant_id)
        if not override:
            query = query.filter((models.Transaction.category == "Uncategorized") | (models.Transaction.category == None))
        
        query = query.filter(or_(*filters))
        target_txns = query.all()
        affected_count = 0
        for txn in target_txns:
            txn.category = rule.category
            if rule.exclude_from_reports:
                txn.exclude_from_reports = True
            if rule.is_transfer and rule.to_account_id:
                txn.is_transfer = True
            db.add(txn)
            affected_count += 1
            
        # 2. Update Pending Transactions (Triage)
        pending_filters = []
        for k in keywords:
            pattern = f"%{k}%"
            pending_filters.append(or_(
                ingestion_models.PendingTransaction.description.ilike(pattern),
                ingestion_models.PendingTransaction.recipient.ilike(pattern)
            ))

        pending_query = db.query(ingestion_models.PendingTransaction).filter(
            ingestion_models.PendingTransaction.tenant_id == tenant_id
        )
        if not override:
            pending_query = pending_query.filter(
                (ingestion_models.PendingTransaction.category == "Uncategorized") | 
                (ingestion_models.PendingTransaction.category == None)
            )
        
        pending_query = pending_query.filter(or_(*pending_filters))
        target_pending = pending_query.all()
        for p_txn in target_pending:
            p_txn.category = rule.category
            if rule.exclude_from_reports:
                p_txn.exclude_from_reports = True
            if rule.is_transfer and rule.to_account_id:
                p_txn.is_transfer = True
                p_txn.to_account_id = rule.to_account_id
            db.add(p_txn)
            affected_count += 1

        db.commit()
        return {"success": True, "affected": affected_count, "category": rule.category}

    @staticmethod
    def get_matching_count(db: Session, keywords: List[str], tenant_id: str, only_uncategorized: bool = True) -> int:
        if not keywords: return 0
        
        # Confirmed Transactions
        query = db.query(models.Transaction).filter(models.Transaction.tenant_id == tenant_id)
        if only_uncategorized:
            query = query.filter((models.Transaction.category == "Uncategorized") | (models.Transaction.category == None))
            
        filters = []
        for k in keywords:
            pattern = f"%{k}%"
            filters.append(or_(
                models.Transaction.description.ilike(pattern),
                models.Transaction.recipient.ilike(pattern)
            ))
        query = query.filter(or_(*filters))
        confirmed_count = query.count()

        # Pending Transactions
        pending_query = db.query(ingestion_models.PendingTransaction).filter(
            ingestion_models.PendingTransaction.tenant_id == tenant_id
        )
        if only_uncategorized:
            pending_query = pending_query.filter(
                (ingestion_models.PendingTransaction.category == "Uncategorized") | 
                (ingestion_models.PendingTransaction.category == None)
            )
            
        pending_filters = []
        for k in keywords:
            pattern = f"%{k}%"
            pending_filters.append(or_(
                ingestion_models.PendingTransaction.description.ilike(pattern),
                ingestion_models.PendingTransaction.recipient.ilike(pattern)
            ))
        pending_query = pending_query.filter(or_(*pending_filters))
        pending_count = pending_query.count()

        return confirmed_count + pending_count

    @staticmethod
    def get_matching_preview(db: Session, keywords: List[str], tenant_id: str, skip: int = 0, limit: int = 5, only_uncategorized: bool = True) -> List[dict]:
        if not keywords: return []
        
        # Confirmed
        query = db.query(models.Transaction).filter(models.Transaction.tenant_id == tenant_id)
        if only_uncategorized:
            query = query.filter((models.Transaction.category == "Uncategorized") | (models.Transaction.category == None))
            
        filters = []
        for k in keywords:
            pattern = f"%{k}%"
            filters.append(or_(
                models.Transaction.description.ilike(pattern),
                models.Transaction.recipient.ilike(pattern)
            ))
        query = query.filter(or_(*filters))
        confirmed_matches = query.order_by(models.Transaction.date.desc()).limit(limit + skip).all()

        # Pending
        pending_query = db.query(ingestion_models.PendingTransaction).filter(
            ingestion_models.PendingTransaction.tenant_id == tenant_id
        )
        if only_uncategorized:
            pending_query = pending_query.filter(
                (ingestion_models.PendingTransaction.category == "Uncategorized") | 
                (ingestion_models.PendingTransaction.category == None)
            )
            
        pending_filters = []
        for k in keywords:
            pattern = f"%{k}%"
            pending_filters.append(or_(
                ingestion_models.PendingTransaction.description.ilike(pattern),
                ingestion_models.PendingTransaction.recipient.ilike(pattern)
            ))
        pending_query = pending_query.filter(or_(*pending_filters))
        pending_matches = pending_query.order_by(ingestion_models.PendingTransaction.date.desc()).limit(limit + skip).all()

        # Combine and Sort
        combined = []
        for m in confirmed_matches:
            combined.append({
                "id": m.id,
                "date": m.date,
                "description": m.description,
                "recipient": m.recipient,
                "amount": m.amount,
                "category": m.category,
                "tenant_id": m.tenant_id,
                "account_id": m.account_id,
                "is_pending": False
            })
        for m in pending_matches:
            combined.append({
                "id": m.id,
                "date": m.date,
                "description": m.description,
                "recipient": m.recipient,
                "amount": m.amount,
                "category": m.category,
                "tenant_id": m.tenant_id,
                "account_id": m.account_id,
                "is_pending": True
            })
            
        combined.sort(key=lambda x: x["date"], reverse=True)
        return combined[skip:skip+limit]

    @staticmethod
    def bulk_rename(db: Session, old_name: str, new_name: str, tenant_id: str, sync_to_parser: bool = False) -> int:
        from sqlalchemy import or_
        pattern = f"%{old_name}%"
        query = db.query(models.Transaction).filter(
            models.Transaction.tenant_id == tenant_id,
            or_(
                models.Transaction.recipient.ilike(pattern),
                models.Transaction.description.ilike(pattern)
            )
        )
        
        txns = query.all()
        for t in txns:
            if t.recipient == old_name:
                t.recipient = new_name
            if t.description == old_name:
                t.description = new_name
            db.add(t)
        
        db.commit()
        
        if sync_to_parser and old_name != new_name:
             try:
                 from backend.app.modules.ingestion.parser_service import ExternalParserService
                 ExternalParserService.create_alias(tenant_id, old_name, new_name)
             except Exception as e:
                 logger.error(f"Failed to sync alias to parser: {e}")
                 
        return len(txns)
