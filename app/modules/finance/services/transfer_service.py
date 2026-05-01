from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from backend.app.core.database import db_write_lock
from backend.app.modules.finance.models import Transaction
from backend.app.modules.ingestion.models import PendingTransaction

class TransferService:
    """
    Modular logic for executing transfers between accounts.
    """
    
    @staticmethod
    def approve_transfer(db: Session, pending: PendingTransaction, tenant_id: str, commit: bool = True) -> Transaction:
        """
        Creates two linked transactions representing the transfer atomically from a pending transaction.
        """
        if not pending.is_transfer or not pending.to_account_id:
            raise ValueError("Pending transaction is not marked as a transfer or missing destination account.")

        return TransferService.create_transfer(
            db, 
            tenant_id,
            account_id=pending.account_id,
            to_account_id=pending.to_account_id,
            amount=pending.amount,
            date=pending.date,
            description=pending.description,
            recipient=pending.recipient,
            external_id=pending.external_id,
            source=pending.source,
            exclude_from_reports=pending.exclude_from_reports,
            latitude=pending.latitude,
            longitude=pending.longitude,
            exclude_pending_id=pending.id,
            source_balance_is_synced=getattr(pending, 'balance_is_synced', False),
            commit=commit
        )

    @staticmethod
    def create_transfer(
        db: Session, 
        tenant_id: str,
        account_id: str,
        to_account_id: str,
        amount: float,
        date: datetime,
        description: Optional[str] = None,
        recipient: Optional[str] = None,
        external_id: Optional[str] = None,
        source: str = "MANUAL",
        exclude_from_reports: bool = True,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        exclude_pending_id: Optional[str] = None,
        source_balance_is_synced: bool = False,
        commit: bool = True
    ) -> Transaction:
        """
        Creates two linked transactions representing the transfer atomically.
        """
        from backend.app.modules.finance.services.transaction_service import TransactionService
        from backend.app.modules.finance import schemas

        with db_write_lock:
            try:
                # 1. Create Source Transaction (Debit/Outflow from perspective of source account)
                source_create = schemas.TransactionCreate(
                    account_id=account_id,
                    amount=-amount,
                    date=date,
                    description=description or f"Transfer to {to_account_id} (Linked)",
                    recipient=recipient,
                    category="Transfer",
                    is_transfer=True,
                    external_id=external_id,
                    source=source,
                    exclude_from_reports=exclude_from_reports,
                    latitude=latitude,
                    longitude=longitude
                )
                
                source_txn = TransactionService.create_transaction(
                    db, source_create, tenant_id, 
                    exclude_pending_id=exclude_pending_id,
                    update_balance=not source_balance_is_synced,
                    commit=False 
                )
                
                # 2. Create Target Transaction (Credit/Inflow from perspective of target account)
                target_create = schemas.TransactionCreate(
                    account_id=to_account_id,
                    amount=amount, 
                    date=date,
                    description=description or f"Transfer from {account_id} (Linked)",
                    recipient=recipient,
                    category="Transfer",
                    is_transfer=True,
                    external_id=f"LINKED-{external_id}" if external_id else None,
                    source=source,
                    exclude_from_reports=exclude_from_reports,
                    latitude=latitude,
                    longitude=longitude
                )
                
                target_txn = TransactionService.create_transaction(
                    db, target_create, tenant_id,
                    exclude_pending_id=exclude_pending_id,
                    update_balance=True,
                    commit=False 
                )
                
                # 3. Link them
                source_txn.linked_transaction_id = target_txn.id
                target_txn.linked_transaction_id = source_txn.id
                
                db.add(source_txn)
                db.add(target_txn)
                
                # 4. Final Atomic Commit
                if commit:
                    db.commit()
                    db.refresh(source_txn)
                
                return source_txn
            except Exception:
                db.rollback()
                raise
