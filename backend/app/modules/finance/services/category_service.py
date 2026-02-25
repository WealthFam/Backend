from typing import List, Optional, Dict
import json
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from backend.app.modules.finance import models, schemas

class CategoryService:
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
            # Seed defaults
            defaults = [
                ("Food & Dining", "🍔"), ("Groceries", "🥦"), ("Transport", "🚌"), 
                ("Shopping", "🛍️"), ("Utilities", "💡"), ("Housing", "🏠"),
                ("Healthcare", "🏥"), ("Entertainment", "🎬"), ("Salary", "💰"),
                ("Investment", "📈"), ("Education", "🎓"), ("Dividend", "💵"),
                ("FD Matured", "🏦"), ("Rent", "🏘️"), ("Gift", "🎁"),
                 ("Other", "📦")
            ]
            new_cats = []
            for name, icon in defaults:
                c = models.Category(tenant_id=tenant_id, name=name, icon=icon)
                db.add(c)
                new_cats.append(c)
            db.commit()
            return new_cats
        return cats

    @staticmethod
    def create_category(db: Session, category: schemas.CategoryCreate, tenant_id: str) -> models.Category:
        db_cat = models.Category(
            **category.model_dump(),
            tenant_id=tenant_id
        )
        db.add(db_cat)
        db.commit()
        db.refresh(db_cat)
        return db_cat

    @staticmethod
    def update_category(db: Session, category_id: str, update: schemas.CategoryUpdate, tenant_id: str) -> Optional[models.Category]:
        db_cat = db.query(models.Category).filter(models.Category.id == category_id, models.Category.tenant_id == tenant_id).first()
        if not db_cat: return None
        
        data = update.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(db_cat, k, v)
            
        db.commit()
        db.refresh(db_cat)
        return db_cat

    @staticmethod
    def delete_category(db: Session, category_id: str, tenant_id: str) -> bool:
        db_cat = db.query(models.Category).filter(models.Category.id == category_id, models.Category.tenant_id == tenant_id).first()
        if not db_cat: return False
        db.delete(db_cat)
        db.commit()
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

    # --- Rules ---
    @staticmethod
    def create_category_rule(db: Session, rule: schemas.CategoryRuleCreate, tenant_id: str) -> models.CategoryRule:
        data = rule.model_dump()
        if isinstance(data.get('keywords'), list):
            data['keywords'] = json.dumps(data['keywords'])
            
        db_rule = models.CategoryRule(
            **data,
            tenant_id=tenant_id
        )
             
        db.add(db_rule)
        db.commit()
        db.refresh(db_rule)
        
        # Manually deserialize keywords for Pydantic response
        try:
             db_rule.keywords = json.loads(db_rule.keywords)
        except:
             db_rule.keywords = []
             
        return db_rule

    @staticmethod
    def get_category_rules(db: Session, tenant_id: str) -> List[models.CategoryRule]:
        rules = db.query(models.CategoryRule).filter(models.CategoryRule.tenant_id == tenant_id).order_by(models.CategoryRule.priority.desc()).all()
        for r in rules:
             try:
                 r.keywords = json.loads(r.keywords)
             except:
                 r.keywords = []
        return rules

    @staticmethod
    def update_category_rule(db: Session, rule_id: str, rule_update: schemas.CategoryRuleUpdate, tenant_id: str) -> Optional[models.CategoryRule]:
        db_rule = db.query(models.CategoryRule).filter(
            models.CategoryRule.id == rule_id,
            models.CategoryRule.tenant_id == tenant_id
        ).first()
        
        if not db_rule:
            return None
            
        update_data = rule_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if key == 'keywords' and value is not None:
                setattr(db_rule, key, json.dumps(value))
            else:
                setattr(db_rule, key, value)
                
        db.commit()
        db.refresh(db_rule)
        
        # Deserialize for response
        try:
             db_rule.keywords = json.loads(db_rule.keywords)
        except:
             db_rule.keywords = []
             
        return db_rule

    @staticmethod
    def delete_category_rule(db: Session, rule_id: str, tenant_id: str) -> bool:
        db_rule = db.query(models.CategoryRule).filter(
            models.CategoryRule.id == rule_id,
            models.CategoryRule.tenant_id == tenant_id
        ).first()
        
        if not db_rule:
            return False
            
        db.delete(db_rule)
        db.commit()
        return True

    @staticmethod
    def ignore_suggestion(db: Session, pattern: str, tenant_id: str):
        exists = db.query(models.IgnoredSuggestion).filter(
            models.IgnoredSuggestion.tenant_id == tenant_id,
            models.IgnoredSuggestion.pattern == pattern
        ).first()
        if not exists:
            db.add(models.IgnoredSuggestion(tenant_id=tenant_id, pattern=pattern))
            db.commit()
            
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
        clean_map = AIService.clean_merchant_names(db, tenant_id, descriptions)

        # 3. Aggregate by clean name
        aggregated = {} 
        
        existing_rules = CategoryService.get_category_rules(db, tenant_id)
        ignored = db.query(models.IgnoredSuggestion).filter(models.IgnoredSuggestion.tenant_id == tenant_id).all()
        
        # Flatten existing keywords for exclusion
        exclusion_set = set()
        for r in existing_rules:
            for kw in (r.keywords or []): 
                if isinstance(kw, str): exclusion_set.add(kw.lower())
        for i in ignored:
            exclusion_set.add(i.pattern.lower())

        for c in candidates:
            clean_name = clean_map.get(c.description, AIService.heuristic_clean_merchant(c.description))
            
            # Skip if already ruled or ignored
            if clean_name.lower() in exclusion_set or c.description.lower() in exclusion_set:
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
                "keywords": json.loads(r.keywords) if isinstance(r.keywords, str) else r.keywords,
                "priority": int(r.priority),
                "exclude_from_reports": r.exclude_from_reports,
                "is_transfer": r.is_transfer,
                "to_account_id": r.to_account_id
            }
            for r in rules
        ]

    @staticmethod
    def import_category_rules(db: Session, rules_data: List[dict], tenant_id: str):
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
