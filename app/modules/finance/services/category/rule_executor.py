"""
Centralized Rule Execution Engine.

Consolidates all rule-matching and rule-application logic from TransactionService
into a dedicated, reusable service. Handles:
- Retrospective rule application (ledger + triage re-categorization)
- Triage-to-Ledger auto-approval (the core new feature)
- Match counting and preview generation
- Rule performance statistics via RuleHitLog

Ref: PRACTICES.md §3 (Ironclad Service Pattern), §11 (Circular Dep Handling)
"""

import json
import logging
import uuid
from datetime import datetime, timezone as dt_timezone
from typing import List, Optional

from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from backend.app.core.database import db_write_lock
from backend.app.core.timezone import utcnow
from backend.app.modules.finance import models, schemas
from backend.app.modules.ingestion import models as ingestion_models

logger = logging.getLogger(__name__)


class RuleExecutor:
    """Centralized engine for all category rule operations."""

    # ---- Internal Helpers ----

    @staticmethod
    def _parse_keywords(rule: models.CategoryRule) -> List[str]:
        """Safely parse keywords from a rule's JSON string."""
        if not rule.keywords:
            return []
        if isinstance(rule.keywords, list):
            return rule.keywords
        try:
            val = json.loads(rule.keywords)
            return val if isinstance(val, list) else []
        except (json.JSONDecodeError, TypeError):
            return []

    @staticmethod
    def _build_keyword_filters(keywords: List[str], model_class):
        """Build OR filters for keyword matching against description/recipient."""
        filters = []
        for k in keywords:
            pattern = f"%{k}%"
            filters.append(or_(
                model_class.description.ilike(pattern),
                model_class.recipient.ilike(pattern)
            ))
        return filters

    @staticmethod
    def _update_hit_log(db: Session, rule_id: str, tenant_id: str, count: int):
        """Upsert the RuleHitLog for a given rule."""
        log = db.query(models.RuleHitLog).filter(
            models.RuleHitLog.rule_id == rule_id,
            models.RuleHitLog.tenant_id == tenant_id
        ).first()

        if log:
            log.hit_count = (log.hit_count or 0) + count
            log.last_hit_at = utcnow()
        else:
            log = models.RuleHitLog(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                rule_id=rule_id,
                hit_count=count,
                last_hit_at=utcnow()
            )
            db.add(log)

    # ---- Triage Scanning (Read-Only) ----

    @staticmethod
    def scan_triage_for_rule(db: Session, rule_id: str, tenant_id: str) -> dict:
        """
        Read-only scan: Find PendingTransactions matching a single rule's keywords.
        Returns { rule_id, rule_name, category, matching_count, preview: [...] }
        """
        rule = db.query(models.CategoryRule).filter(
            models.CategoryRule.id == rule_id,
            models.CategoryRule.tenant_id == tenant_id
        ).first()

        if not rule:
            return {"rule_id": rule_id, "rule_name": "Unknown", "category": "", "matching_count": 0, "preview": []}

        keywords = RuleExecutor._parse_keywords(rule)
        if not keywords:
            return {"rule_id": rule_id, "rule_name": rule.name, "category": rule.category, "matching_count": 0, "preview": []}

        filters = RuleExecutor._build_keyword_filters(keywords, ingestion_models.PendingTransaction)

        query = db.query(ingestion_models.PendingTransaction).filter(
            ingestion_models.PendingTransaction.tenant_id == tenant_id,
            or_(*filters)
        )

        total = query.count()
        preview_items = query.order_by(ingestion_models.PendingTransaction.date.desc()).limit(10).all()

        preview = [{
            "id": p.id,
            "date": str(p.date) if p.date else None,
            "description": p.description,
            "recipient": p.recipient,
            "amount": float(p.amount) if p.amount else 0,
            "category": p.category,
            "account_id": p.account_id,
            "source": p.source
        } for p in preview_items]

        return {
            "rule_id": str(rule.id),
            "rule_name": rule.name,
            "category": rule.category,
            "matching_count": total,
            "preview": preview
        }

    @staticmethod
    def scan_all_triage(db: Session, tenant_id: str) -> dict:
        """
        Read-only scan: Run ALL rules against the triage queue.
        Returns { total_pending, total_matches, rules_with_matches: [...] }
        """
        total_pending = db.query(ingestion_models.PendingTransaction).filter(
            ingestion_models.PendingTransaction.tenant_id == tenant_id
        ).count()

        rules = db.query(models.CategoryRule).filter(
            models.CategoryRule.tenant_id == tenant_id
        ).order_by(models.CategoryRule.priority.desc()).all()

        results = []
        total_matches = 0

        for rule in rules:
            scan = RuleExecutor.scan_triage_for_rule(db, str(rule.id), tenant_id)
            if scan["matching_count"] > 0:
                results.append(scan)
                total_matches += scan["matching_count"]

        return {
            "total_pending": total_pending,
            "total_matches": total_matches,
            "rules_with_matches": results
        }

    # ---- Triage Application (Write — The Core New Feature) ----

    @staticmethod
    def apply_rule_to_triage(db: Session, rule_id: str, tenant_id: str) -> dict:
        """
        Apply a rule to matching PendingTransactions and auto-approve them into the ledger.
        
        Uses TransactionService.approve_pending_transaction() for each match to ensure
        full balance updates, dedup checks, and transfer handling.
        
        Returns { success, affected, category, errors }
        """
        rule = db.query(models.CategoryRule).filter(
            models.CategoryRule.id == rule_id,
            models.CategoryRule.tenant_id == tenant_id
        ).first()

        if not rule:
            return {"success": False, "affected": 0, "message": "Rule not found"}

        keywords = RuleExecutor._parse_keywords(rule)
        if not keywords:
            return {"success": True, "affected": 0, "category": rule.category}

        filters = RuleExecutor._build_keyword_filters(keywords, ingestion_models.PendingTransaction)

        matching = db.query(ingestion_models.PendingTransaction).filter(
            ingestion_models.PendingTransaction.tenant_id == tenant_id,
            or_(*filters)
        ).all()

        if not matching:
            return {"success": True, "affected": 0, "category": rule.category}

        # Inline import to break circular dependency (PRACTICES.md §11)
        from backend.app.modules.finance.services.transaction_service import TransactionService

        affected = 0
        errors = []

        for pending in matching:
            try:
                result = TransactionService.approve_pending_transaction(
                    db,
                    pending_id=str(pending.id),
                    tenant_id=tenant_id,
                    category_override=rule.category,
                    is_transfer_override=rule.is_transfer,
                    to_account_id_override=rule.to_account_id if rule.is_transfer else None,
                    exclude_from_reports_override=rule.exclude_from_reports if rule.exclude_from_reports else None
                )
                if result:
                    affected += 1
            except Exception as e:
                logger.error(f"Failed to approve pending {pending.id} via rule {rule_id}: {e}")
                errors.append({"pending_id": str(pending.id), "error": str(e)})

        # Track hits
        if affected > 0:
            with db_write_lock:
                try:
                    RuleExecutor._update_hit_log(db, rule_id, tenant_id, affected)
                    db.commit()
                except Exception:
                    db.rollback()

        return {
            "success": True,
            "affected": affected,
            "category": rule.category,
            "errors": errors
        }

    # ---- Retrospective Application (Moved from TransactionService) ----

    @staticmethod
    def apply_rule_retrospectively(db: Session, rule_id: str, tenant_id: str, override: bool = False) -> dict:
        """
        Apply a rule to existing ledger transactions and pending transactions (re-categorize only).
        Moved from TransactionService.apply_rule_retrospectively.
        """
        rule = db.query(models.CategoryRule).filter(
            models.CategoryRule.id == rule_id,
            models.CategoryRule.tenant_id == tenant_id
        ).first()

        if not rule:
            return {"success": False, "message": "Rule not found"}

        keywords = json.loads(rule.keywords) if isinstance(rule.keywords, str) else rule.keywords
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
        affected_count = 0
        with db_write_lock:
            try:
                query = db.query(models.Transaction).filter(models.Transaction.tenant_id == tenant_id)
                if not override:
                    query = query.filter(
                        (models.Transaction.category == "Uncategorized") | (models.Transaction.category == None)
                    )
                query = query.filter(or_(*filters))
                target_txns = query.all()
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

                # Track hits
                if affected_count > 0:
                    RuleExecutor._update_hit_log(db, rule_id, tenant_id, affected_count)

                db.commit()
                return {"success": True, "affected": affected_count, "category": rule.category}
            except Exception:
                db.rollback()
                raise

    # ---- Match Count & Preview (Moved from TransactionService) ----

    @staticmethod
    def get_matching_count(db: Session, keywords: List[str], tenant_id: str, only_uncategorized: bool = True) -> int:
        """Count transactions matching keywords across both ledger and triage."""
        if not keywords:
            return 0

        # Confirmed Transactions
        query = db.query(models.Transaction).filter(models.Transaction.tenant_id == tenant_id)
        if only_uncategorized:
            query = query.filter(
                (models.Transaction.category == "Uncategorized") | (models.Transaction.category == None)
            )
        filters = RuleExecutor._build_keyword_filters(keywords, models.Transaction)
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
        pending_filters = RuleExecutor._build_keyword_filters(keywords, ingestion_models.PendingTransaction)
        pending_query = pending_query.filter(or_(*pending_filters))
        pending_count = pending_query.count()

        return confirmed_count + pending_count

    @staticmethod
    def get_matching_preview(db: Session, keywords: List[str], tenant_id: str,
                             skip: int = 0, limit: int = 5, only_uncategorized: bool = True) -> List[dict]:
        """Preview transactions matching keywords across both ledger and triage."""
        if not keywords:
            return []

        # Confirmed
        query = db.query(models.Transaction).filter(models.Transaction.tenant_id == tenant_id)
        if only_uncategorized:
            query = query.filter(
                (models.Transaction.category == "Uncategorized") | (models.Transaction.category == None)
            )
        filters = RuleExecutor._build_keyword_filters(keywords, models.Transaction)
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
        pending_filters = RuleExecutor._build_keyword_filters(keywords, ingestion_models.PendingTransaction)
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
        return combined[skip:skip + limit]

    # ---- Rule Statistics ----

    @staticmethod
    def get_rule_stats(db: Session, tenant_id: str) -> dict:
        """Aggregate rule performance statistics from RuleHitLog."""
        total_rules = db.query(models.CategoryRule).filter(
            models.CategoryRule.tenant_id == tenant_id
        ).count()

        # Get all hit logs for this tenant
        hit_logs = db.query(models.RuleHitLog).filter(
            models.RuleHitLog.tenant_id == tenant_id
        ).all()

        total_hits = sum(log.hit_count or 0 for log in hit_logs)
        rules_with_hits = set(log.rule_id for log in hit_logs if (log.hit_count or 0) > 0)
        rules_with_zero_hits = total_rules - len(rules_with_hits)
        avg_hit_rate = (len(rules_with_hits) / total_rules * 100) if total_rules > 0 else 0

        # Top performing rules
        top_logs = sorted(hit_logs, key=lambda x: x.hit_count or 0, reverse=True)[:5]
        top_rules = []
        for log in top_logs:
            rule = db.query(models.CategoryRule).filter(
                models.CategoryRule.id == log.rule_id
            ).first()
            if rule:
                top_rules.append({
                    "name": rule.name,
                    "hit_count": log.hit_count or 0,
                    "category": rule.category
                })

        # Get pending triage count (Thorough: Only count transactions matching existing rules)
        scan_results = RuleExecutor.scan_all_triage(db, tenant_id)
        matched_count = scan_results.get("total_matches", 0)

        return {
            "total_rules": total_rules,
            "total_hits": total_hits,
            "rules_with_zero_hits": rules_with_zero_hits,
            "avg_hit_rate": round(avg_hit_rate, 1),
            "top_rules": top_rules,
            "pending_triage": matched_count
        }

    @staticmethod
    def get_rule_hit_info(db: Session, rule_id: str, tenant_id: str) -> dict:
        """Get hit info for a specific rule (used by CategoryService for enrichment)."""
        log = db.query(models.RuleHitLog).filter(
            models.RuleHitLog.rule_id == rule_id,
            models.RuleHitLog.tenant_id == tenant_id
        ).first()

        if log:
            return {"hit_count": log.hit_count or 0, "last_hit_at": log.last_hit_at}
        return {"hit_count": 0, "last_hit_at": None}
