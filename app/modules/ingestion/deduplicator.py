from sqlalchemy.orm import Session
from sqlalchemy import func, or_
import hashlib
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple, List
from backend.app.modules.finance import models as finance_models
from backend.app.modules.ingestion import models as ingestion_models
from backend.app.modules.ingestion.base import ParsedTransaction

class TransactionDeduplicator:
    """
    Unified service to check for duplicate transactions across various sources.
    Checks by Reference ID, Content Hash, and exact field matching.
    """

    @staticmethod
    def normalize_vendor(name: str) -> str:
        """
        Normalize vendor names to ensure hash stability across sources.
        Removes bank-specific prefixes, filler words, and standardizes whitespace.
        """
        if not name:
            return ""
        
        # 1. Remove source-specific prefixes and common filler words
        # (e.g., "HDFC: ", "Info: ", "on ", "at ", "spent at ", "to ")
        name = name.lower()
        
        # Strip prefixes like "info: ", "merchant: ", "learned: ", "spent at ", etc.
        name = re.sub(r'^[a-z\s]+:\s*', '', name)
        
        # Strip common leading filler words
        name = re.sub(r'^(on|at|to|spent|spent at|paid to|info|for|using)\s+', '', name)
        
        # 2. Keep only alphanumeric and space
        name = "".join(c for c in name if c.isalnum() or c.isspace())
        
        # 3. Standardize whitespace and convert to uppercase
        return " ".join(name.split()).upper()

    @staticmethod
    def generate_hash(tenant_id: str, account_id: str, date: datetime, amount: float, description: Optional[str], recipient: Optional[str] = None) -> str:
        """
        Generate a stable content hash for a transaction based on its fields.
        Uses date.date() to ensure hash stability across sources (SMS vs Email) 
        which often have different timestamps for the same transaction.
        """
        txn_type = "DEBIT" if amount < 0 else "CREDIT"
        
        # Combine recipient and description to find the best representative name
        raw_name = recipient or description or ""
        name = TransactionDeduplicator.normalize_vendor(raw_name)
        
        # Canonical format: tenant:account:date:amount:type:name
        # Using date.date() is CRITICAL for deduplicating SMS vs Email.
        payload = f"{tenant_id}:{account_id}:{date.date().isoformat()}:{abs(amount):.2f}:{txn_type}:{name}"
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
        recipient: Optional[str] = None,
        allow_cross_day: bool = True
    ) -> Optional[finance_models.Transaction]:
        """
        Check if an existing transaction matches basic fields (Amount, Date, Desc/Recipient).
        Resilient: Checks across description/recipient fields and allows +/- 1 day window.
        """
        date_list = [date.date()]
        if allow_cross_day:
            date_list.append((date - timedelta(days=1)).date())
            date_list.append((date + timedelta(days=1)).date())

        query = db.query(finance_models.Transaction).filter(
            finance_models.Transaction.tenant_id == tenant_id,
            finance_models.Transaction.account_id == account_id,
            finance_models.Transaction.amount == amount,
            func.date(finance_models.Transaction.date).in_(date_list),
            finance_models.Transaction.is_deleted == False
        )
        
        # Normalize the input name for robust comparison
        norm_input = TransactionDeduplicator.normalize_vendor(recipient or description or "")
        if not norm_input:
            return None
        
        results = query.all()
        for existing in results:
            # Check if EITHER existing description OR existing recipient matches our normalized input
            norm_existing_desc = TransactionDeduplicator.normalize_vendor(existing.description)
            norm_existing_recp = TransactionDeduplicator.normalize_vendor(existing.recipient)
            
            if norm_input == norm_existing_desc or norm_input == norm_existing_recp:
                return existing
            
        return None

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
                or_(finance_models.Transaction.external_id == ref_id, finance_models.Transaction.external_id == external_id),
                finance_models.Transaction.is_deleted == False
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
            
            # CROSS-SOURCE DEDUPLICATION: If we have a Ref ID, also check if it's a partial match 
            # or exists in another source format (some sources might truncate).
            # (Already handled by normalize_ref_id and exact match above)

        # 2. Content Hash Check
        content_hash = TransactionDeduplicator.generate_hash(
            tenant_id, account_id, date, amount, description, recipient
        )
        
        existing_hash = db.query(finance_models.Transaction).filter(
            finance_models.Transaction.tenant_id == tenant_id,
            finance_models.Transaction.content_hash == content_hash,
            finance_models.Transaction.is_deleted == False
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

        # 3. Fields match (Date, Amount, Desc) with 1-day window
        confirmed_match = TransactionDeduplicator.check_fields_match(db, tenant_id, account_id, amount, date, description, recipient)
        if confirmed_match:
             return True, f"Identical fields match transaction {confirmed_match.id} (Resilient Match)", str(confirmed_match.id)
             
        # Check Pending table fields too
        date_list = [date.date(), (date - timedelta(days=1)).date(), (date + timedelta(days=1)).date()]
        query_pending_match = db.query(ingestion_models.PendingTransaction).filter(
            ingestion_models.PendingTransaction.tenant_id == tenant_id,
            ingestion_models.PendingTransaction.account_id == account_id,
            ingestion_models.PendingTransaction.amount == amount,
            func.date(ingestion_models.PendingTransaction.date).in_(date_list)
        )
        
        if exclude_pending_id:
            query_pending_match = query_pending_match.filter(ingestion_models.PendingTransaction.id != exclude_pending_id)
            
        pending_results = query_pending_match.all()
        norm_input = TransactionDeduplicator.normalize_vendor(recipient or description or "")
        
        for p in pending_results:
            norm_p = TransactionDeduplicator.normalize_vendor(p.recipient or p.description or "")
            if (norm_input == norm_p and norm_input != "") or (p.recipient == recipient or p.description == description):
                return True, f"Identical fields match triage item {p.id} (Resilient Match)", str(p.id)

        return False, None, None
