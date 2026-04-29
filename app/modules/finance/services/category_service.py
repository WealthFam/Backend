from typing import List, Optional
import json
import logging

logger = logging.getLogger(__name__)

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from backend.app.core.database import db_write_lock
from backend.app.modules.finance import models, schemas
from backend.app.modules.ingestion import models as ingestion_models
from fastapi import HTTPException

class CategoryService:
    @staticmethod
    def _safe_load_keywords(keywords_str):
        if not keywords_str:
            return []
        if not isinstance(keywords_str, str):
            return keywords_str
        try:
            val = json.loads(keywords_str)
            return val if isinstance(val, list) else []
        except:
            return []

    # --- Category Management ---
    @staticmethod
    def get_categories(db: Session, tenant_id: str, tree: bool = False) -> List[models.Category]:
        if tree:
            # Return only root categories, subcategories will be loaded via relationship
            return db.query(models.Category).options(joinedload(models.Category.subcategories)).filter(
                models.Category.tenant_id == tenant_id,
                models.Category.parent_id == None
            ).all()
            
        cats = db.query(models.Category).filter(models.Category.tenant_id == tenant_id).all()
        if not cats:
            # Seed defaults with proper types
            # Format: (Name, Icon, Type)
            defaults = [
                ("Food & Dining", "🍔", "expense"), ("Groceries", "🥦", "expense"), 
                ("Transport", "🚌", "expense"), ("Shopping", "🛍️", "expense"), 
                ("Utilities", "💡", "expense"), ("Housing", "🏠", "expense"),
                ("Healthcare", "🏥", "expense"), ("Entertainment", "🎬", "expense"), 
                ("Salary", "💰", "income"), ("Investment", "📈", "investment"), 
                ("Education", "🎓", "expense"), ("Dividend", "💵", "income"),
                ("FD Matured", "🏦", "income"), ("Rent", "🏘️", "expense"), 
                ("Gift", "🎁", "income"), ("Other", "📦", "expense")
            ]
            new_cats = []
            with db_write_lock:
                try:
                    for name, icon, cat_type in defaults:
                        c = models.Category(tenant_id=tenant_id, name=name, icon=icon, type=cat_type)
                        db.add(c)
                        new_cats.append(c)
                    db.commit()
                except Exception:
                    db.rollback()
                    raise
            return new_cats
        return cats

    @staticmethod
    def create_category(db: Session, category: schemas.CategoryCreate, tenant_id: str) -> models.Category:
        db_cat = models.Category(
            **category.model_dump(),
            tenant_id=tenant_id
        )
        with db_write_lock:
            try:
                db.add(db_cat)
                db.commit()
                db.refresh(db_cat)
            except Exception:
                db.rollback()
                raise
        return db_cat

    @staticmethod
    def update_category(db: Session, category_id: str, update: schemas.CategoryUpdate, tenant_id: str) -> Optional[models.Category]:
        db_cat = db.query(models.Category).filter(models.Category.id == category_id, models.Category.tenant_id == tenant_id).first()
        if not db_cat: return None
        
        old_name = db_cat.name
        data = update.model_dump(exclude_unset=True)
        new_name = data.get("name")
        
        with db_write_lock:
            try:
                # 1. If name changed, update all linked entities (Cascade Update)
                if new_name and new_name != old_name:
                    # Update Ledger Transactions
                    db.query(models.Transaction).filter(
                        models.Transaction.tenant_id == tenant_id,
                        models.Transaction.category == old_name
                    ).update({models.Transaction.category: new_name}, synchronize_session=False)

                    # Update Triage Transactions
                    db.query(ingestion_models.PendingTransaction).filter(
                        ingestion_models.PendingTransaction.tenant_id == tenant_id,
                        ingestion_models.PendingTransaction.category == old_name
                    ).update({ingestion_models.PendingTransaction.category: new_name}, synchronize_session=False)

                    # Update Classification Rules
                    db.query(models.CategoryRule).filter(
                        models.CategoryRule.tenant_id == tenant_id,
                        models.CategoryRule.category == old_name
                    ).update({models.CategoryRule.category: new_name}, synchronize_session=False)

                    # Update Budgets
                    db.query(models.Budget).filter(
                        models.Budget.tenant_id == tenant_id,
                        models.Budget.category == old_name
                    ).update({models.Budget.category: new_name}, synchronize_session=False)

                # 2. Update the Category itself
                for k, v in data.items():
                    setattr(db_cat, k, v)
                
                db.commit()
                db.refresh(db_cat)
            except Exception:
                db.rollback()
                raise
        return db_cat

    @staticmethod
    def get_category_usage(db: Session, category_id: str, tenant_id: str) -> dict:
        db_cat = db.query(models.Category).filter(models.Category.id == category_id, models.Category.tenant_id == tenant_id).first()
        if not db_cat:
            raise HTTPException(status_code=404, detail="Category not found")
            
        reasons = []
        
        # Check subcategories
        child_count = db.query(models.Category).filter(models.Category.parent_id == category_id).count()
        if child_count > 0:
            reasons.append(f"Contains {child_count} active sub-folder(s)")
            
        # Check transactions
        txn_count = db.query(models.Transaction).filter(
            models.Transaction.tenant_id == tenant_id,
            models.Transaction.category == db_cat.name
        ).count()
        if txn_count > 0:
            reasons.append(f"Linked to {txn_count} existing transaction(s)")
            
        # Check pending transactions
        pending_count = db.query(ingestion_models.PendingTransaction).filter(
            ingestion_models.PendingTransaction.tenant_id == tenant_id,
            ingestion_models.PendingTransaction.category == db_cat.name
        ).count()
        if pending_count > 0:
            reasons.append(f"Used in {pending_count} pending triage item(s)")
            
        # Check rules
        rule_count = db.query(models.CategoryRule).filter(
            models.CategoryRule.tenant_id == tenant_id,
            models.CategoryRule.category == db_cat.name
        ).count()
        if rule_count > 0:
            reasons.append(f"Linked to {rule_count} classification rule(s)")
            
        return {
            "is_safe": len(reasons) == 0,
            "reasons": reasons,
            "category_name": db_cat.name
        }

    @staticmethod
    def delete_category(db: Session, category_id: str, tenant_id: str) -> bool:
        db_cat = db.query(models.Category).filter(models.Category.id == category_id, models.Category.tenant_id == tenant_id).first()
        if not db_cat: return False
        
        # 1. Check for subcategories
        has_children = db.query(models.Category).filter(models.Category.parent_id == category_id).first()
        if has_children:
            raise HTTPException(status_code=400, detail="This category contains sub-folders. Please delete or move them first.")

        # 2. Check for active transactions (Ledger)
        has_txns = db.query(models.Transaction).filter(
            models.Transaction.tenant_id == tenant_id,
            models.Transaction.category == db_cat.name
        ).first()
        if has_txns:
            raise HTTPException(status_code=400, detail="This category is linked to existing transactions. Please re-categorize them first.")

        # 3. Check for pending transactions (Triage)
        has_pending = db.query(ingestion_models.PendingTransaction).filter(
            ingestion_models.PendingTransaction.tenant_id == tenant_id,
            ingestion_models.PendingTransaction.category == db_cat.name
        ).first()
        if has_pending:
            raise HTTPException(status_code=400, detail="This category is currently being used in the Triage queue.")

        # 4. Check for active rules
        has_rules = db.query(models.CategoryRule).filter(
            models.CategoryRule.tenant_id == tenant_id,
            models.CategoryRule.category == db_cat.name
        ).first()
        if has_rules:
            raise HTTPException(status_code=400, detail="An active classification rule is using this category.")

        with db_write_lock:
            try:
                db.delete(db_cat)
                db.commit()
            except Exception:
                db.rollback()
                raise
        return True

    @staticmethod
    def export_categories(db: Session, tenant_id: str) -> List[dict]:
        cats = db.query(models.Category).filter(models.Category.tenant_id == tenant_id).all()
        return [
            {
                "name": c.name,
                "icon": c.icon,
                "color": c.color,
                "type": c.type,
                "parent_name": c.parent.name if c.parent else None
            }
            for c in cats
        ]

    @staticmethod
    def import_categories(db: Session, categories_data: List[dict], tenant_id: str):
        # First pass: Create all categories
        name_map = {}
        with db_write_lock:
            try:
                for c_data in categories_data:
                    existing = db.query(models.Category).filter(
                        models.Category.tenant_id == tenant_id,
                        models.Category.name == c_data["name"]
                    ).first()
                    
                    if not existing:
                        cat = models.Category(
                            tenant_id=tenant_id,
                            name=c_data["name"],
                            icon=c_data.get("icon", "🏷️"),
                            color=c_data.get("color", "#3B82F6"),
                            type=c_data.get("type", "expense")
                        )
                        db.add(cat)
                        db.flush() # Get ID
                        name_map[cat.name] = cat
                    else:
                        name_map[existing.name] = existing
                
                # Second pass: Link parents
                for c_data in categories_data:
                    parent_name = c_data.get("parent_name")
                    if parent_name and parent_name in name_map:
                        cat = name_map[c_data["name"]]
                        cat.parent_id = name_map[parent_name].id
                
                db.commit()
            except Exception:
                db.rollback()
                raise

    # --- Rules ---
    @staticmethod
    def create_category_rule(db: Session, rule: schemas.CategoryRuleCreate, tenant_id: str, commit: bool = True) -> models.CategoryRule:
        data = rule.model_dump()
        if isinstance(data.get('keywords'), list):
            data['keywords'] = json.dumps(data['keywords'])
            
        db_rule = models.CategoryRule(
            **data,
            tenant_id=tenant_id
        )
             
        with db_write_lock:
            try:
                db.add(db_rule)
                if commit:
                    db.commit()
                    db.refresh(db_rule)
            except Exception:
                db.rollback()
                raise
        
        if not commit:
            return db_rule

        # Expunge to prevent accidental sync of deserialized list back to DB
        db.expunge(db_rule)

        # Manually deserialize keywords for Pydantic response
        db_rule.is_valid = True
        db_rule.validation_error = None
        try:
             db_rule.keywords = json.loads(db_rule.keywords)
        except:
             db_rule.keywords = []
             db_rule.is_valid = False
             db_rule.validation_error = "Malformed JSON"
        
        # Cast Numeric to int for strict validation
        db_rule.priority = int(db_rule.priority)
             
        return db_rule

    @staticmethod
    def get_category_rules(db: Session, tenant_id: str, skip: int = 0, limit: int = 50, category: Optional[str] = None, search: Optional[str] = None) -> dict:
        query = db.query(models.CategoryRule).filter(models.CategoryRule.tenant_id == tenant_id)
        
        if category and category != 'all':
            query = query.filter(models.CategoryRule.category == category)
            
        if search:
            search_query = f"%{search}%"
            query = query.filter(
                (models.CategoryRule.name.ilike(search_query)) |
                (models.CategoryRule.category.ilike(search_query)) |
                (models.CategoryRule.keywords.ilike(search_query))
            )
            
        total = query.count()
        rules = query.order_by(models.CategoryRule.priority.desc()).offset(skip).limit(limit).all()
        
        # Batch-load hit logs for enrichment
        rule_ids = [str(r.id) for r in rules]
        hit_logs = {}
        if rule_ids:
            logs = db.query(models.RuleHitLog).filter(
                models.RuleHitLog.tenant_id == tenant_id,
                models.RuleHitLog.rule_id.in_(rule_ids)
            ).all()
            for log in logs:
                hit_logs[log.rule_id] = log

        for r in rules:
             r.is_valid = True
             r.validation_error = None
             db.expunge(r)
             try:
                 keywords = json.loads(r.keywords)
                 r.keywords = keywords
                 if not isinstance(keywords, list):
                     r.is_valid = False
                     r.validation_error = "Keywords must be a JSON list"
                 elif len(keywords) == 0:
                     r.is_valid = False
                     r.validation_error = "Rule has no keywords"
             except Exception as e:
                 r.is_valid = False
                 r.validation_error = f"Malformed JSON in keywords: {str(e)}"
                 r.keywords = []
             
             # Cast Numeric to int for strict validation
             r.priority = int(r.priority)

             # Enrich with hit stats from RuleHitLog
             hit_log = hit_logs.get(str(r.id))
             r.hit_count = hit_log.hit_count if hit_log else 0
             r.last_hit_at = hit_log.last_hit_at if hit_log else None
             
        return {"data": rules, "total": total}

    @staticmethod
    def update_category_rule(db: Session, rule_id: str, rule_update: schemas.CategoryRuleUpdate, tenant_id: str, commit: bool = True) -> Optional[models.CategoryRule]:
        db_rule = db.query(models.CategoryRule).filter(
            models.CategoryRule.id == rule_id,
            models.CategoryRule.tenant_id == tenant_id
        ).first()
        
        if not db_rule:
            return None
            
        update_data = rule_update.model_dump(exclude_unset=True)
        with db_write_lock:
            try:
                for key, value in update_data.items():
                    if key == 'keywords' and value is not None:
                        setattr(db_rule, key, json.dumps(value))
                    else:
                        setattr(db_rule, key, value)
                        
                if commit:
                    db.commit()
                    db.refresh(db_rule)
            except Exception:
                db.rollback()
                raise
        
        if not commit:
            return db_rule

        # Expunge to prevent accidental sync of deserialized list back to DB
        db.expunge(db_rule)

        # Deserialize for response
        db_rule.is_valid = True
        db_rule.validation_error = None
        try:
             db_rule.keywords = json.loads(db_rule.keywords)
             if not isinstance(db_rule.keywords, list) or len(db_rule.keywords) == 0:
                 db_rule.is_valid = False
                 db_rule.validation_error = "Rule must have at least one keyword"
        except:
             db_rule.keywords = []
             db_rule.is_valid = False
             db_rule.validation_error = "Malformed JSON"
             
        # Cast Numeric to int for strict validation
        db_rule.priority = int(db_rule.priority)
             
        return db_rule

    @staticmethod
    def delete_category_rule(db: Session, rule_id: str, tenant_id: str) -> bool:
        db_rule = db.query(models.CategoryRule).filter(
            models.CategoryRule.id == rule_id,
            models.CategoryRule.tenant_id == tenant_id
        ).first()
        
        if not db_rule:
            return False
            
        with db_write_lock:
            try:
                db.delete(db_rule)
                db.commit()
            except Exception:
                db.rollback()
                raise
        return True

    @staticmethod
    def ignore_suggestion(db: Session, pattern: str, tenant_id: str):
        exists = db.query(models.IgnoredSuggestion).filter(
            models.IgnoredSuggestion.tenant_id == tenant_id,
            models.IgnoredSuggestion.pattern == pattern
        ).first()
        if not exists:
            with db_write_lock:
                try:
                    db.add(models.IgnoredSuggestion(tenant_id=tenant_id, pattern=pattern))
                    db.commit()
                except Exception:
                    db.rollback()
                    raise
            
    @staticmethod
    def get_rule_suggestions(db: Session, tenant_id: str) -> List[dict]:
        """
        Analyze transaction history to suggest new rules using AI-enhanced grouping.
        """
        from backend.app.modules.ingestion.ai_service import AIService
        
        # 1. Fetch raw candidates
        candidates = db.query(
            models.Transaction.description,
            models.Transaction.category,
            func.count(models.Transaction.id).label("count")
        ).filter(
            models.Transaction.tenant_id == tenant_id,
            models.Transaction.category != "Uncategorized",
            models.Transaction.category != None
        ).group_by(
            models.Transaction.description, 
            models.Transaction.category
        ).having(
            func.count(models.Transaction.id) >= 1
        ).order_by(
            func.count(models.Transaction.id).desc()
        ).limit(50).all()

        if not candidates: return []

        # 2. Extract clean names
        descriptions = list(set([c.description for c in candidates if c.description]))
        try:
            clean_map = AIService.clean_merchant_names(db, tenant_id, descriptions)
        except Exception as e:
            # Fallback to heuristic cleaning if AI fails (e.g. 429 quota exceeded)
            from backend.app.modules.ingestion.ai_service import AIService
            clean_map = {d: AIService.heuristic_clean_merchant(d) for d in descriptions}
            # Log as warning not error if it's just a quota issue
            logger.warning(f"AI cleaning failed for suggestions, falling back to heuristic: {e}")

        # 3. Aggregate by clean name
        from backend.app.modules.finance.services.category.rule_executor import RuleExecutor
        
        rules_objects = db.query(models.CategoryRule).filter(models.CategoryRule.tenant_id == tenant_id).all()
        ignored = db.query(models.IgnoredSuggestion).filter(models.IgnoredSuggestion.tenant_id == tenant_id).all()
        ignored_patterns = [i.pattern.lower() for i in ignored]
        
        aggregated = {} 
        for c in candidates:
            clean_name = clean_map.get(c.description, AIService.heuristic_clean_merchant(c.description))
            desc_lower = c.description.lower()
            clean_lower = clean_name.lower()
            
            # Check if ignored
            if any(p in desc_lower or p in clean_lower for p in ignored_patterns):
                continue
                
            # Check if already covered by an existing rule
            is_covered = False
            for r in rules_objects:
                # 1. Exact Name match (Suggested name matches rule name)
                if r.name and r.name.lower() == clean_lower:
                    is_covered = True
                    break
                # 2. Keyword match (Does the rule apply to this description?)
                kws = RuleExecutor._parse_keywords(r)
                if any(kw.lower() in desc_lower for kw in kws):
                    is_covered = True
                    break
            
            if is_covered:
                continue

            if clean_name not in aggregated:
                aggregated[clean_name] = {
                    "category": c.category,
                    "count": 0,
                    "keywords": {clean_name},
                    "reason": f"Frequent merchant '{clean_name}' detected."
                }
            
            aggregated[clean_name]["count"] += c.count
            # If multiple descriptions map to same clean name, we can add them to keywords or just stick to clean name
            # aggregated[clean_name]["keywords"].add(c.description) # Maybe too noisy? Let's just use clean name
            # aggregated[clean_name]["keywords"].add(c.description)

        # 4. Final collection
        suggestions = []
        for name, data in aggregated.items():
            # Apply a slightly higher threshold for suggestions if AI is used? 
            # Or just keep it at 2+ for visibility.
            if data["count"] < 2: continue 
            
            confidence = min(0.95, 0.4 + (data["count"] * 0.1))
            level = "High" if data["count"] >= 5 else "Medium"
            if data["count"] >= 10: level = "Very High"
            
            suggestions.append({
                "name": f"Auto-tag {name}",
                "category": data["category"],
                "keywords": list(data["keywords"]),
                "count": data["count"],
                "confidence": confidence,
                "confidence_level": level,
                "reason": data["reason"]
            })

        # Sort by count
        suggestions.sort(key=lambda x: x["count"], reverse=True)
        return suggestions[:15]

    @staticmethod
    def export_category_rules(db: Session, tenant_id: str) -> List[dict]:
        rules = db.query(models.CategoryRule).filter(models.CategoryRule.tenant_id == tenant_id).all()
        return [
            {
                "name": r.name,
                "category": r.category,
                "keywords": CategoryService._safe_load_keywords(r.keywords),
                "priority": int(r.priority),
                "exclude_from_reports": r.exclude_from_reports,
                "is_transfer": r.is_transfer,
                "to_account_id": r.to_account_id
            }
            for r in rules
        ]

    @staticmethod
    def import_category_rules(db: Session, rules_data: List[dict], tenant_id: str):
        with db_write_lock:
            try:
                for r_data in rules_data:
                    existing = db.query(models.CategoryRule).filter(
                        models.CategoryRule.tenant_id == tenant_id,
                        models.CategoryRule.name == r_data["name"]
                    ).first()
                    
                    keywords = r_data.get("keywords", [])
                    if isinstance(keywords, list):
                        keywords = json.dumps(keywords)

                    if not existing:
                        rule = models.CategoryRule(
                            tenant_id=tenant_id,
                            name=r_data["name"],
                            category=r_data["category"],
                            keywords=keywords,
                            priority=r_data.get("priority", 0),
                            exclude_from_reports=r_data.get("exclude_from_reports", False),
                            is_transfer=r_data.get("is_transfer", False),
                            to_account_id=r_data.get("to_account_id")
                        )
                        db.add(rule)
                    else:
                        existing.category = r_data["category"]
                        existing.keywords = keywords
                        existing.priority = r_data.get("priority", existing.priority)
                        existing.exclude_from_reports = r_data.get("exclude_from_reports", existing.exclude_from_reports)
                        existing.is_transfer = r_data.get("is_transfer", existing.is_transfer)
                        existing.to_account_id = r_data.get("to_account_id", existing.to_account_id)
                
                db.commit()
            except Exception:
                db.rollback()
                raise
