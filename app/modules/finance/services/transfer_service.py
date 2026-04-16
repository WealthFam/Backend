from sqlalchemy.orm import Session
from backend.app.core.database import db_write_lock
from backend.app.modules.finance.models import Transaction
from backend.app.modules.ingestion.models import PendingTransaction

class TransferService:
    """
    Modular logic for executing transfers between accounts.
    """
    
    @staticmethod
    def approve_transfer(db: Session, pending: PendingTransaction, tenant_id: str) -> Transaction:
        """
        Creates two linked transactions representing the transfer atomically.
        """
        if not pending.is_transfer or not pending.to_account_id:
            raise ValueError("Pending transaction is not marked as a transfer or missing destination account.")

        from backend.app.modules.finance.services.transaction_service import TransactionService
        from backend.app.modules.finance import schemas

        with db_write_lock:
            try:
                # 1. Create Source Transaction (Debit)
                source_create = schemas.TransactionCreate(
                    account_id=pending.account_id,
                    amount=pending.amount,
                    date=pending.date,
                    description=f"Transfer to {pending.to_account_id} (Linked)",
                    recipient=pending.recipient,
                    category="Transfer",
                    is_transfer=True,
                    external_id=pending.external_id,
                    source=pending.source,
                    exclude_from_reports=pending.exclude_from_reports,
                    latitude=pending.latitude,
                    longitude=pending.longitude
                )
                
                update_source_balance = not getattr(pending, 'balance_is_synced', False)
                source_txn = TransactionService.create_transaction(
                    db, source_create, tenant_id, 
                    exclude_pending_id=pending.id,
                    update_balance=update_source_balance,
                    commit=False # Don't commit yet
                )
                
                # 2. Create Target Transaction (Credit)
                target_create = schemas.TransactionCreate(
                    account_id=pending.to_account_id,
                    amount=-pending.amount, 
                    date=pending.date,
                    description=f"Transfer from {pending.account_id} (Linked)",
                    recipient=pending.recipient,
                    category="Transfer",
                    is_transfer=True,
                    external_id=f"LINKED-{pending.external_id}" if pending.external_id else None,
                    source=pending.source,
                    exclude_from_reports=pending.exclude_from_reports,
                    latitude=pending.latitude,
                    longitude=pending.longitude
                )
                
                target_txn = TransactionService.create_transaction(
                    db, target_create, tenant_id,
                    exclude_pending_id=pending.id,
                    update_balance=True,
                    commit=False # Don't commit yet
                )
                
                # 3. Link them
                source_txn.linked_transaction_id = target_txn.id
                target_txn.linked_transaction_id = source_txn.id
                
                db.add(source_txn)
                db.add(target_txn)
                
                # 4. Final Atomic Commit
                db.commit()
                db.refresh(source_txn)
                
                return source_txn
            except Exception:
                db.rollback()
                raise
