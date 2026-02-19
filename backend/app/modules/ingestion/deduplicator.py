from sqlalchemy.orm import Session
from sqlalchemy import func, or_
import hashlib
from datetime import datetime
from typing import Optional, Tuple
from backend.app.modules.finance import models as finance_models
from backend.app.modules.ingestion import models as ingestion_models
from backend.app.modules.ingestion.base import ParsedTransaction

class TransactionDeduplicator:
    """
    Unified service to check for duplicate transactions across various sources.
    Checks by Reference ID, Content Hash, and exact field matching.
    """

    @staticmethod
    def generate_hash(tenant_id: str, account_id: str, date: datetime, amount: float, description: Optional[str], recipient: Optional[str] = None) -> str:
        """
        Generate a stable content hash for a transaction based on its fields.
        Standardizes amount to 2 decimal places and date to ISO format.
        Now explicitly includes transaction type (Debit/Credit).
        """
        txn_type = "DEBIT" if amount < 0 else "CREDIT"
        name = recipient or description or ""
        # Canonical format: tenant:account:date:amount:type:name
        # We use absolute amount + explicit type to be crystal clear.
        # Use full ISO format to capture time if available.
        payload = f"{tenant_id}:{account_id}:{date.isoformat()}:{abs(amount):.2f}:{txn_type}:{name.strip()}"
        return hashlib.md5(payload.encode()).hexdigest()

    @staticmethod
    def normalize_ref_id(ref_id: Optional[str]) -> Optional[str]:
        if not ref_id:
            return None
        clean_id = str(ref_id).strip()
        if clean_id.isdigit():
            # Standardize numeric IDs (remove leading zeros)
            return clean_id.lstrip('0') or "0"
        return clean_id

    @staticmethod
    def check_fields_match(
        db: Session,
        tenant_id: str,
        account_id: str,
        amount: float,
        date: datetime,
        description: Optional[str] = None,
        recipient: Optional[str] = None
    ) -> Optional[finance_models.Transaction]:
        """
        Check if an existing transaction matches basic fields (Amount, Date, Desc/Recipient).
        Resilient: Only compares the DATE part (ignoring time).
        """
        # Use a small epsilon or exact match for decimal/float?
        # DuckDB usually handles float equality well for stored Decimals if precision is kept.
        if date.time() == datetime.min.time():
            # If incoming date is exactly midnight, assume Date-only match (legacy/CSV behavior)
            query = db.query(finance_models.Transaction).filter(
                finance_models.Transaction.tenant_id == tenant_id,
                finance_models.Transaction.account_id == account_id,
                finance_models.Transaction.amount == amount,
                func.date(finance_models.Transaction.date) == date.date()
            )
        else:
            # Precise timestamp match
            query = db.query(finance_models.Transaction).filter(
                finance_models.Transaction.tenant_id == tenant_id,
                finance_models.Transaction.account_id == account_id,
                finance_models.Transaction.amount == amount,
                finance_models.Transaction.date == date
            )
        
        # Match Description OR Recipient
        if recipient:
            query = query.filter(
                or_(
                    finance_models.Transaction.description == description,
                    finance_models.Transaction.recipient == recipient
                )
            )
        elif description:
            query = query.filter(finance_models.Transaction.description == description)
            
        return query.first()

    @staticmethod
    def check_duplicate(
        db: Session, 
        tenant_id: str, 
        parsed: ParsedTransaction, 
        account_id: str, 
        final_amount: float
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Main entry point for SMS/Email ingestion deduplication.
        Uses the consolidated check_raw_duplicate logic.
        """
        return TransactionDeduplicator.check_raw_duplicate(
            db, 
            tenant_id, 
            account_id, 
            final_amount, 
            parsed.date, 
            parsed.description, 
            parsed.recipient, 
            parsed.ref_id
        )

    @staticmethod
    def check_raw_duplicate(
        db: Session,
        tenant_id: str,
        account_id: str,
        amount: float,
        date: datetime,
        description: Optional[str] = None,
        recipient: Optional[str] = None,
        external_id: Optional[str] = None,
        exclude_pending_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Check for duplicates using raw fields (useful for manual entry or generic builders).
        Returns (is_duplicate, reason, existing_id)
        """
        # 1. Reference ID
        ref_id = TransactionDeduplicator.normalize_ref_id(external_id)
        if ref_id:
            # Confirmed
            existing = db.query(finance_models.Transaction).filter(
                finance_models.Transaction.tenant_id == tenant_id,
                or_(finance_models.Transaction.external_id == ref_id, finance_models.Transaction.external_id == external_id)
            ).first()
            if existing: return True, f"Ref ID {ref_id} already confirmed", str(existing.id)
            
            query_pending = db.query(ingestion_models.PendingTransaction).filter(
                ingestion_models.PendingTransaction.tenant_id == tenant_id,
                or_(ingestion_models.PendingTransaction.external_id == ref_id, ingestion_models.PendingTransaction.external_id == external_id)
            )
            if exclude_pending_id:
                query_pending = query_pending.filter(ingestion_models.PendingTransaction.id != exclude_pending_id)
            
            pending = query_pending.first()
            if pending: return True, f"Ref ID {ref_id} already in triage", str(pending.id)

        # 2. Content Hash Check
        content_hash = TransactionDeduplicator.generate_hash(
            tenant_id, account_id, date, amount, description, recipient
        )
        
        existing_hash = db.query(finance_models.Transaction).filter(
            finance_models.Transaction.tenant_id == tenant_id,
            finance_models.Transaction.content_hash == content_hash
        ).first()
        if existing_hash: return True, "Standardized field-hash match", str(existing_hash.id)

        query_pending_hash = db.query(ingestion_models.PendingTransaction).filter(
            ingestion_models.PendingTransaction.tenant_id == tenant_id,
            ingestion_models.PendingTransaction.content_hash == content_hash
        )
        if exclude_pending_id:
            query_pending_hash = query_pending_hash.filter(ingestion_models.PendingTransaction.id != exclude_pending_id)
            
        pending_hash = query_pending_hash.first()
        if pending_hash: return True, "Standardized field-hash match in triage", str(pending_hash.id)

        # 3. Fields match (Date, Amount, Desc)
        confirmed_match = TransactionDeduplicator.check_fields_match(db, tenant_id, account_id, amount, date, description, recipient)
        if confirmed_match:
             return True, f"Identical fields match transaction {confirmed_match.id}", str(confirmed_match.id)
             
        # Check Pending table fields too
        query_pending_match = db.query(ingestion_models.PendingTransaction).filter(
            ingestion_models.PendingTransaction.tenant_id == tenant_id,
            ingestion_models.PendingTransaction.account_id == account_id,
            ingestion_models.PendingTransaction.amount == amount,
            func.date(ingestion_models.PendingTransaction.date) == date.date(),
            or_(
                ingestion_models.PendingTransaction.description == description,
                ingestion_models.PendingTransaction.recipient == recipient
            ) if recipient else (ingestion_models.PendingTransaction.description == description)
        )
        if exclude_pending_id:
            query_pending_match = query_pending_match.filter(ingestion_models.PendingTransaction.id != exclude_pending_id)
            
        pending_match = query_pending_match.first()
        if pending_match:
             return True, f"Identical fields match triage item {pending_match.id}", str(pending_match.id)

        return False, None, None
