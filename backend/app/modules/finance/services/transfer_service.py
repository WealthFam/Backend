from sqlalchemy.orm import Session
from backend.app.modules.finance.models import Transaction, TransactionType
from backend.app.modules.ingestion.models import PendingTransaction
import uuid
from datetime import datetime

class TransferService:
    """
    Modular logic for executing transfers between accounts.
    """
    
    @staticmethod
    def approve_transfer(db: Session, pending: PendingTransaction, tenant_id: str) -> Transaction:
        """
        Creates two linked transactions representing the transfer using TransactionService
        to ensure balance updates and other logic are applied.
        Returns the primary (source) transaction.
        """
        if not pending.is_transfer or not pending.to_account_id:
            raise ValueError("Pending transaction is not marked as a transfer or missing destination account.")

        from backend.app.modules.finance.services.transaction_service import TransactionService
        from backend.app.modules.finance import schemas

        # 1. Create Source Transaction (Debit from original account)
        # We start with the pending data
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
            exclude_from_reports=pending.exclude_from_reports
        )
        
        # We need to handle the balance sync flag from pending for the source side
        # If pending.balance_is_synced is True, we DON'T update balance for source
        update_source_balance = not getattr(pending, 'balance_is_synced', False)

        source_txn = TransactionService.create_transaction(
            db, source_create, tenant_id, 
            exclude_pending_id=pending.id,
            update_balance=update_source_balance
        )
        
        # 2. Create Target Transaction (Mirror/Credit to destination account)
        # Target usually doesn't have a 'balance_is_synced' flag from the same pending txn 
        # unless it was a dual-side import (unlikely). So we generally update balance for target.
        target_create = schemas.TransactionCreate(
            account_id=pending.to_account_id,
            amount=-pending.amount, # Invert amount
            date=pending.date,
            description=f"Transfer from {pending.account_id} (Linked)",
            recipient=pending.recipient,
            category="Transfer",
            is_transfer=True,
            external_id=f"LINKED-{pending.external_id}" if pending.external_id else None,
            source=pending.source,
            exclude_from_reports=pending.exclude_from_reports
        )
        
        target_txn = TransactionService.create_transaction(
            db, target_create, tenant_id,
            exclude_pending_id=pending.id,
            update_balance=True 
        )
        
        # Link them
        source_txn.linked_transaction_id = target_txn.id
        target_txn.linked_transaction_id = source_txn.id
        
        db.add(source_txn)
        db.add(target_txn)
        
        return source_txn
