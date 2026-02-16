from typing import List, Optional
from datetime import datetime
import json
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import or_
import logging
from backend.app.modules.finance import models, schemas

logger = logging.getLogger(__name__)
from backend.app.modules.finance.models import TransactionType
from backend.app.modules.finance.services.category_service import CategoryService
from backend.app.modules.finance.services.transfer_service import TransferService
from backend.app.modules.ingestion import models as ingestion_models

class TransactionService:
    @staticmethod
    def create_transaction(db: Session, transaction: schemas.TransactionCreate, tenant_id: str, exclude_pending_id: Optional[str] = None, update_balance: bool = True):
        # 1. Unified Deduplication Check (Ref ID, Hash-Fallback, and Fields)
        from backend.app.modules.ingestion.deduplicator import TransactionDeduplicator
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
            raise ValueError(f"Duplicate transaction: {reason}")
            
        # 2. Content Hash Generation (for storage)
        txn_hash = getattr(transaction, 'content_hash', None)
        if not txn_hash:
            txn_hash = TransactionDeduplicator.generate_hash(
                tenant_id, str(transaction.account_id), transaction.date, transaction.amount, transaction.description, transaction.recipient
            )

        # Serialize tags if present
        tags_str = json.dumps(transaction.tags) if transaction.tags else None
        
        # --- Auto-Categorization Logic ---
        final_category = transaction.category
        final_exclude = transaction.exclude_from_reports or transaction.is_transfer
        
        if (not final_category or final_category == "Uncategorized") and (transaction.description or transaction.recipient):
            rules = db.query(models.CategoryRule).filter(models.CategoryRule.tenant_id == tenant_id).order_by(models.CategoryRule.priority.desc()).all()
            
            desc_lower = (transaction.description or "").lower()
            recipient_lower = (transaction.recipient or "").lower()
            
            for rule in rules:
                try:
                    keywords = json.loads(rule.keywords)
                    if any(k.lower() in desc_lower or k.lower() in recipient_lower for k in keywords):
                        final_category = rule.category
                        if rule.exclude_from_reports:
                            final_exclude = True
                        break
                except Exception as e:
                    pass
        # ---------------------------------
        
        txn_type = models.TransactionType.DEBIT if transaction.amount < 0 else models.TransactionType.CREDIT

        db_transaction = models.Transaction(
            account_id=str(transaction.account_id),
            tenant_id=tenant_id,
            amount=transaction.amount,
            date=transaction.date,
            description=transaction.description,
            recipient=transaction.recipient,
            category=final_category,
            tags=tags_str,
            external_id=transaction.external_id if transaction.external_id else str(uuid.uuid4()), # Ensure external_id or UUID? Model might allow null, but safer to have ID
            type=txn_type,
            is_transfer=transaction.is_transfer,
            linked_transaction_id=getattr(transaction, 'linked_transaction_id', None),
            source=transaction.source if hasattr(transaction, 'source') else "MANUAL",
            content_hash=txn_hash,
            exclude_from_reports=final_exclude,
            is_emi=getattr(transaction, 'is_emi', False),
            loan_id=getattr(transaction, 'loan_id', None)
        )
        
        # Update Account Balance
        if update_balance:
            db_account = db.query(models.Account).filter(models.Account.id == str(transaction.account_id)).first()
            if db_account:
                # ANCHOR CHECK: If this transaction is older than (or equal to) the last sync,
                # we assume it's already factored into the anchored balance.
                if db_account.last_synced_at and transaction.date <= db_account.last_synced_at:
                    pass # Do not update balance
                else:
                    current_bal = db_account.balance or 0
                    # If it's a liability (Loan/Credit Card), adding money (Credit) reduces the balance owed
                    # Spending money (Debit/Negative) increases the balance owed
                    if db_account.type in [models.AccountType.LOAN, models.AccountType.CREDIT_CARD]:
                        db_account.balance = current_bal - transaction.amount
                    else:
                        db_account.balance = current_bal + transaction.amount
                    db.add(db_account)

        db.add(db_transaction)
        db.commit()
        db.refresh(db_transaction)
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
        if user_id in [None, "null", "undefined", ""]:
            user_id = None
        
        # import logging
        # logger = logging.getLogger(__name__)
        # logger.info(f"get_transactions: tenant_id={tenant_id}, user_id={user_id}, account_id={account_id}")

        query = db.query(models.Transaction).filter(models.Transaction.tenant_id == tenant_id)
        
        if user_role == "CHILD":
            query = query.join(models.Account, models.Transaction.account_id == models.Account.id)\
                         .filter(models.Account.type.notin_(["INVESTMENT", "CREDIT"]))

        if account_id:
            query = query.filter(models.Transaction.account_id == account_id)
        if start_date:
            query = query.filter(models.Transaction.date >= start_date)
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
        if user_id in [None, "null", "undefined", ""]:
            user_id = None
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
            query = query.filter(models.Transaction.date >= start_date)
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
            query = query.filter(models.Transaction.category == category)
            
        if exclude_from_reports:
            query = query.filter(models.Transaction.exclude_from_reports == False)
        if exclude_transfers:
            query = query.filter(models.Transaction.is_transfer == False)
            
        return query.count()

    @staticmethod
    def bulk_delete_transactions(db: Session, transaction_ids: List[str], tenant_id: str) -> int:
        if not transaction_ids: return 0
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
                anchor_date = account.last_synced_at
                
                for t in account_txns:
                    # Only revert balance if txn is NEWER than anchor.
                    # If older/equal, it's baked into the anchor snapshot.
                    if not anchor_date or t.date > anchor_date:
                        # Revert logic:
                        # Create (Loan): bal = bal - amt  => Undo: bal = bal + amt
                        # Create (Bank): bal = bal + amt  => Undo: bal = bal - amt
                        if account.type in [models.AccountType.LOAN, models.AccountType.CREDIT_CARD]:
                            balance_change += t.amount
                        else:
                            balance_change -= t.amount
                
                if balance_change != 0:
                    current = account.balance or 0
                    account.balance = current + balance_change
                    db.add(account)
            
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
        db_txn = db.query(models.Transaction).filter(
            models.Transaction.id == txn_id,
            models.Transaction.tenant_id == tenant_id
        ).first()
        
        if not db_txn:
            return None
            
        # Snapshot old state for balance adjustment
        old_amount = db_txn.amount
        old_date = db_txn.date
        
        update_data = txn_update.model_dump(exclude_unset=True)
        
        # ... (Transfer logic remains same) ...
        # But we need to keep the code structure valid. 
        # Since I'm replacing a huge block, I'll just insert the logic helper around the existing code
        # implicitly by how I structure the replacement.
        
        # Re-implementing the transfer logic block matching original file...
        is_transfer_update = update_data.get('is_transfer')
        to_account_id = update_data.get('to_account_id')
        
        if is_transfer_update is True:
            db_txn.is_transfer = True
            db_txn.exclude_from_reports = True
            
            # Case A: User selected an EXISTING transaction to link (Manual Match)
            if update_data.get('linked_transaction_id'):
                # 1. Unlink any old one
                if db_txn.linked_transaction_id:
                     old_linked = db.query(models.Transaction).filter(models.Transaction.id == db_txn.linked_transaction_id).first()
                     if old_linked:
                        old_linked.linked_transaction_id = None
                        db.add(old_linked)

                # 2. Link the new target
                target_id = update_data['linked_transaction_id']
                target_txn = db.query(models.Transaction).filter(models.Transaction.id == target_id).first()
                
                if target_txn:
                    db_txn.linked_transaction_id = target_txn.id
                    target_txn.linked_transaction_id = db_txn.id
                    target_txn.is_transfer = True
                    target_txn.category = "Transfer"
                    target_txn.exclude_from_reports = True 
                    db.add(target_txn)

            # Case B: User selected an ACCOUNT to transfer to (Auto Create)
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
        
        for key, value in update_data.items():
            if key in ['is_transfer', 'to_account_id']: continue
            if key == 'tags' and value is not None:
                setattr(db_txn, key, json.dumps(value))
            elif key in ['linked_transaction_id', 'expense_group_id', 'loan_id'] and value == "":
                setattr(db_txn, key, None)
            else:
                setattr(db_txn, key, value)
        
        # --- Balance Adjustment Logic ---
        # Did amount or date change?
        new_amount = db_txn.amount
        new_date = db_txn.date
        
        if new_amount != old_amount or new_date != old_date:
            account = db.query(models.Account).filter(models.Account.id == db_txn.account_id).first()
            if account:
                anchor_date = account.last_synced_at
                balance_delta = 0
                
                # 1. Revert Old (if it was contributing)
                if not anchor_date or old_date > anchor_date:
                    if account.type in [models.AccountType.LOAN, models.AccountType.CREDIT_CARD]:
                        balance_delta += old_amount
                    else:
                        balance_delta -= old_amount

                # 2. Apply New (if it should contribute)
                if not anchor_date or new_date > anchor_date:
                    if account.type in [models.AccountType.LOAN, models.AccountType.CREDIT_CARD]:
                        balance_delta -= new_amount
                    else:
                        balance_delta += new_amount
                        
                if balance_delta != 0:
                    account.balance = (account.balance or 0) + balance_delta
                    db.add(account)
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
        query = db.query(ingestion_models.PendingTransaction).filter(
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
        create_rule: bool = False
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
            account_id=pending.account_id,
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
            exclude_from_reports=final_exclude
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
            
        # Find transactions that match keywords
        query = db.query(models.Transaction).filter(
            models.Transaction.tenant_id == tenant_id
        )

        # If not overriding, only search for uncategorized
        if not override:
            query = query.filter((models.Transaction.category == "Uncategorized") | (models.Transaction.category == None))
        
        # Build OR clause for keywords
        filters = []
        for k in keywords:
            pattern = f"%{k}%"
            filters.append(models.Transaction.description.ilike(pattern))
            filters.append(models.Transaction.recipient.ilike(pattern))
            
        query = query.filter(or_(*filters))
        
        target_txns = query.all()
        affected_count = 0
        for txn in target_txns:
            txn.category = rule.category
            if rule.exclude_from_reports:
                txn.exclude_from_reports = True
            if rule.is_transfer and rule.to_account_id:
                txn.is_transfer = True
                # Note: We don't auto-create the other leg here to avoid mess, 
                # but we could if needed. For retrospective, usually just the category/hidden flag is enough.
            db.add(txn)
            affected_count += 1
            
        db.commit()
        return {"success": True, "affected": affected_count, "category": rule.category}

    @staticmethod
    def get_matching_count(db: Session, keywords: List[str], tenant_id: str, only_uncategorized: bool = True) -> int:
        if not keywords: return 0
        query = db.query(models.Transaction).filter(
            models.Transaction.tenant_id == tenant_id
        )
        if only_uncategorized:
            query = query.filter((models.Transaction.category == "Uncategorized") | (models.Transaction.category == None))
            
        filters = []
        for k in keywords:
            pattern = f"%{k}%"
            filters.append(models.Transaction.description.ilike(pattern))
            filters.append(models.Transaction.recipient.ilike(pattern))
        query = query.filter(or_(*filters))
        return query.count()

    @staticmethod
    def get_matching_preview(db: Session, keywords: List[str], tenant_id: str, skip: int = 0, limit: int = 5, only_uncategorized: bool = True) -> List[models.Transaction]:
        if not keywords: return []
        query = db.query(models.Transaction).filter(
            models.Transaction.tenant_id == tenant_id
        )
        if only_uncategorized:
            query = query.filter((models.Transaction.category == "Uncategorized") | (models.Transaction.category == None))
            
        filters = []
        for k in keywords:
            pattern = f"%{k}%"
            filters.append(models.Transaction.description.ilike(pattern))
            filters.append(models.Transaction.recipient.ilike(pattern))
        
        query = query.filter(or_(*filters)).order_by(models.Transaction.date.desc())
        return query.offset(skip).limit(limit).all()

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
                 ExternalParserService.create_alias(old_name, new_name)
             except Exception as e:
                 logger.error(f"Failed to sync alias to parser: {e}")
                 
        return len(txns)
