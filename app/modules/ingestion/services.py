import hashlib
import json
import logging
from typing import Optional, Any

from sqlalchemy.orm import Session

from backend.app.core.database import db_write_lock
from backend.app.modules.finance import models as finance_models
from backend.app.modules.finance import schemas as finance_schemas
from backend.app.modules.finance.services.transaction_service import TransactionService
from backend.app.modules.ingestion import models as ingestion_models
from backend.app.modules.ingestion.base import ParsedTransaction
from backend.app.modules.ingestion.transfer_detector import TransferDetector

logger = logging.getLogger(__name__)

class IngestionService:
    @staticmethod
    def log_event(db: Session, tenant_id: str, event_type: str, status: str, message: Optional[str] = None, data: Optional[dict] = None, device_id: Optional[str] = None):
        """
        Log an ingestion event for auditing.
        """
        logger.info(f"INGESTION EVENT: {event_type} | STATUS: {status} | MESSAGE: {message}")
        with db_write_lock:
            event = ingestion_models.IngestionEvent(
                tenant_id=tenant_id,
                device_id=device_id,
                event_type=event_type,
                status=status,
                message=message,
                data_json=json.dumps(data) if data else None
            )
            db.add(event)
            db.commit()

    @staticmethod
    def match_account(db: Session, tenant_id: str, mask: str) -> Optional[finance_models.Account]:
        """
        Find an account belonging to the tenant that ends with the given mask.
        Mask usually is 4 digits like "1234".
        """
        if not mask or len(mask) < 2:
            return None
            
        accounts = db.query(finance_models.Account).filter(
            finance_models.Account.tenant_id == tenant_id,
            finance_models.Account.account_mask != None
        ).all()
        
        # Normalize search mask: last 4 digits
        search_mask = "".join(filter(str.isdigit, mask))[-4:]
        
        for acc in accounts:
            if acc.account_mask and acc.account_mask.endswith(search_mask):
                return acc
        return None

    @staticmethod
    def process_transaction(db: Session, tenant_id: str, parsed: Any, extra_data: Any = None):
        if extra_data is None:
            extra_data = {}
        account = None
        if parsed.account_mask:
            account = IngestionService.match_account(db, tenant_id, parsed.account_mask)
            
        if not account and parsed.account_mask:
            # BLOCK AUTO-DISCOVERY: Account must be pre-linked.
            logger.warning(f"INGESTION BLOCKED: Account ending in '{parsed.account_mask[-4:]}' not found for tenant.")
            return {
                "status": "blocked", 
                "reason": f"Account ending in '{parsed.account_mask[-4:]}' not found. Link account first.",
                "account_mask": parsed.account_mask[-4:]
            }
            
        is_fallback_account = False
        if not account:
            # BLOCK: No account matched.
            reason = "No account mask detected in message." if not parsed.account_mask else f"Account ending in '{parsed.account_mask[-4:]}' not found."
            logger.warning(f"INGESTION BLOCKED: {reason}")
            return {
                "status": "blocked", 
                "reason": f"{reason} Please link the account in settings first.",
                "account_mask": parsed.account_mask[-4:] if parsed.account_mask else None
            }
            
        # Determine amount sign
        final_amount = parsed.amount
        if parsed.type == "DEBIT":
            final_amount = -abs(parsed.amount)
        else:
            final_amount = abs(parsed.amount)

        # DEDUPLICATION CHECK
        from backend.app.modules.ingestion.deduplicator import TransactionDeduplicator
        message_hash = TransactionDeduplicator.generate_hash(
            tenant_id, str(account.id), parsed.date, final_amount, parsed.description, parsed.recipient
        )

        is_dup, reason, existing_id = TransactionDeduplicator.check_duplicate(db, tenant_id, parsed, str(account.id), final_amount)
        
        if is_dup:
            logger.warning(f"INGESTION SKIPPED: Duplicate detected - {reason} (Existing ID: {existing_id})")
            
            # ENHANCEMENT: Update location if missing (handles both Triage and Ledger)
            if extra_data.get("latitude") or extra_data.get("longitude"):
                # 1. Check Triage
                pending = db.query(ingestion_models.PendingTransaction).filter(
                    ingestion_models.PendingTransaction.id == existing_id,
                    ingestion_models.PendingTransaction.tenant_id == tenant_id
                ).first()
                if pending:
                    updated = False
                    if pending.latitude is None and extra_data.get("latitude"):
                        pending.latitude = extra_data.get("latitude")
                        updated = True
                    if pending.longitude is None and extra_data.get("longitude"):
                        pending.longitude = extra_data.get("longitude")
                        updated = True
                    if updated:
                        logger.info(f"Updated location for pending transaction {pending.id}")
                        db.commit()
                else:
                    # 2. Check Ledger
                    from backend.app.modules.finance import models as finance_models
                    logger.info(f"Deduplication: Checking ledger for existing_id={existing_id}")
                    existing = db.query(finance_models.Transaction).filter(
                        finance_models.Transaction.id == existing_id,
                        finance_models.Transaction.tenant_id == tenant_id
                    ).first()
                    if existing:
                        logger.info(f"Deduplication: Found existing transaction {existing.id}. Current lat: {existing.latitude}")
                        updated = False
                        if existing.latitude is None and extra_data.get("latitude"):
                            existing.latitude = extra_data.get("latitude")
                            updated = True
                        if existing.longitude is None and extra_data.get("longitude"):
                            existing.longitude = extra_data.get("longitude")
                            updated = True
                        if updated:
                            logger.info(f"Updated location for existing transaction {existing.id} to {existing.latitude}, {existing.longitude}")
                            db.commit()
                    else:
                        logger.warning(f"Deduplication: Could not find existing transaction {existing_id} in ledger for tenant {tenant_id}")
            
            return {"status": "skipped", "reason": f"Deduplicated: {reason}", "deduplicated": True, "existing_id": existing_id}

        # IGNORE PATTERN CHECK
        check_text = f"{(parsed.recipient or '')} {(parsed.description or '')}".lower()
        ignored_patterns = db.query(ingestion_models.IgnoredPattern).filter(
            ingestion_models.IgnoredPattern.tenant_id == tenant_id
        ).all()
        for ip in ignored_patterns:
            if ip.pattern.lower() in check_text:
                return {"status": "skipped", "reason": f"Ignored by user pattern: {ip.pattern}"}
        
        # Try to detect internal transfer
        all_accounts = db.query(finance_models.Account).filter(finance_models.Account.tenant_id == tenant_id).all()
        all_rules = db.query(finance_models.CategoryRule).filter(finance_models.CategoryRule.tenant_id == tenant_id).all()
        
        is_transfer, to_account_id = TransferDetector.detect(parsed.description, parsed.recipient, all_accounts, all_rules, source_account_id=str(account.id))
        
        # Try to auto-categorize
        category = parsed.category
        if not category or category == "Uncategorized":
            category = TransactionService.get_suggested_category(db, tenant_id, parsed.description, parsed.recipient)
        
        if is_transfer:
            category = "Transfer"
        
        is_auto_ingest = False
        triage_categories = ["uncategorized", "miscellaneous", "misc", "other", "unknown"]
        if category and str(category).strip().lower() not in triage_categories:
            is_auto_ingest = True
            
        if is_fallback_account:
            is_auto_ingest = False
            
        from backend.app.modules.notifications import NotificationService
        balance_synced = False

        if is_auto_ingest:
            # High confidence -> Directly to transactions
            if parsed.balance is not None:
                is_newer = True
                if account.last_synced_at and parsed.date < account.last_synced_at:
                    is_newer = False
                
                if is_newer:
                    with db_write_lock:
                        account.last_synced_balance = parsed.balance
                        account.last_synced_at = parsed.date
                        if parsed.credit_limit:
                            account.last_synced_limit = parsed.credit_limit
                        
                        account.balance = parsed.balance
                        if parsed.credit_limit:
                            account.credit_limit = parsed.credit_limit
                        
                        snapshot = finance_models.BalanceSnapshot(
                            account_id=str(account.id),
                            tenant_id=tenant_id,
                            balance=parsed.balance,
                            timestamp=parsed.date,
                            source=parsed.source or "AUTO"
                        )
                        db.add(snapshot)
                        db.flush()  # Use flush instead of commit to keep session alive for transaction creation
                        balance_synced = True


            txn_create = finance_schemas.TransactionCreate(
                account_id=str(account.id),
                amount=final_amount,
                date=parsed.date,
                description=parsed.description,
                recipient=parsed.recipient,
                category=category,
                external_id=parsed.ref_id,
                source=parsed.source,
                tags=[],
                latitude=extra_data.get("latitude") or extra_data.get("lat"),
                longitude=extra_data.get("longitude") or extra_data.get("lng"),
                content_hash=message_hash,
                is_transfer=is_transfer,
                to_account_id=to_account_id,
                exclude_from_reports=is_transfer
            )
            try:
                db_txn = TransactionService.create_transaction(
                    db, txn_create, tenant_id, 
                    update_balance=not balance_synced,
                    commit=False # Bug 5 Fix: Defer commit until end of flow
                )
                db.commit()

                NotificationService.notify_transaction(
                    db, tenant_id, final_amount, 
                    parsed.description or parsed.recipient, 
                    account.name,
                    user_id=account.owner_id
                )

                return {"status": "success", "transaction_id": str(db_txn.id), "account": account.name}
            except Exception as e:
                db.rollback()
                raise e
        else:
            # Low confidence -> Move to Triage
            pending = ingestion_models.PendingTransaction(
                tenant_id=tenant_id,
                account_id=str(account.id),
                amount=final_amount,
                date=parsed.date,
                description=parsed.description,
                recipient=parsed.recipient,
                category="Uncategorized",
                source=parsed.source,
                raw_message=parsed.raw_message,
                balance=parsed.balance,
                credit_limit=parsed.credit_limit,
                content_hash=message_hash,
                external_id=parsed.ref_id,
                is_transfer=is_transfer,
                to_account_id=to_account_id,
                exclude_from_reports=is_transfer,
                balance_is_synced=balance_synced,
                latitude=extra_data.get("latitude") or extra_data.get("lat"),
                longitude=extra_data.get("longitude") or extra_data.get("lng")
            )
            with db_write_lock:
                db.add(pending)
                db.commit()
            
            NotificationService.notify_triage(
                db, tenant_id, final_amount, 
                parsed.description or parsed.recipient or "Merchant",
                account.name
            )
            
            return {"status": "triage", "message": "Low confidence, entry moved to triage."}

    @staticmethod
    def capture_unparsed(db: Session, tenant_id: str, source: str, raw_content: str, subject: Optional[str] = None, sender: Optional[str] = None, latitude: Optional[float] = None, longitude: Optional[float] = None):
        msg_hash = hashlib.md5(raw_content.encode()).hexdigest()

        check_text = f"{(subject or '')} {(raw_content or '')}".lower()
        ignored_patterns = db.query(ingestion_models.IgnoredPattern).filter(
            ingestion_models.IgnoredPattern.tenant_id == tenant_id
        ).all()
        for ip in ignored_patterns:
            if ip.pattern.lower() in check_text:
                return 
            
        spam_filters = db.query(ingestion_models.SpamFilter).filter(
            ingestion_models.SpamFilter.tenant_id == tenant_id
        ).all()
        for sf in spam_filters:
            sender_match = (not sf.sender or sf.sender == sender)
            subject_match = (not sf.subject or sf.subject == subject)
            if sender_match and subject_match:
                with db_write_lock:
                    sf.count_blocked = (sf.count_blocked or 0) + 1
                    db.commit()
                return 

        existing = db.query(ingestion_models.UnparsedMessage).filter(
            ingestion_models.UnparsedMessage.tenant_id == tenant_id,
            ingestion_models.UnparsedMessage.content_hash == msg_hash
        ).first()
        if existing: return
        
        msg = ingestion_models.UnparsedMessage(
            tenant_id=tenant_id,
            source=source,
            raw_content=raw_content,
            content_hash=msg_hash,
            subject=subject,
            sender=sender,
            latitude=latitude,
            longitude=longitude
        )
        with db_write_lock:
            db.add(msg)
            db.commit()
