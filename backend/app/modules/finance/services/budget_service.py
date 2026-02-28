from typing import List
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from backend.app.modules.finance import models, schemas
from backend.app.core import timezone

class BudgetService:
    @staticmethod
    def get_budget_overview(db: Session, tenant_id: str, year: int = None, month: int = None, user_id: str = None) -> dict:
        if user_id in [None, "null", "undefined", ""]:
            user_id = None
        """
        Get global budget overview data (OVERALL stats).
        """
        now = timezone.utcnow()
        if not year: year = now.year
        if not month: month = now.month
        
        start_of_period = datetime(year, month, 1)
        if month == 12:
            end_of_period = datetime(year + 1, 1, 1)
        else:
            end_of_period = datetime(year, month + 1, 1)
            
        # Spending
        # Separate expenses (negative) and income (positive)
        # Note: SQL sum would mix them. We need to sum conditionally or fetch all.
        
        total_expense = db.query(func.sum(models.Transaction.amount)).filter(
            models.Transaction.tenant_id == tenant_id,
            models.Transaction.date >= start_of_period,
            models.Transaction.date < end_of_period,
            models.Transaction.is_transfer == False,
            models.Transaction.exclude_from_reports == False,
            models.Transaction.amount < 0
        )
        if user_id:
             total_expense = total_expense.join(models.Account, models.Transaction.account_id == models.Account.id).filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))
        total_expense = abs(total_expense.scalar() or 0)
        
        total_income = db.query(func.sum(models.Transaction.amount)).filter(
            models.Transaction.tenant_id == tenant_id,
            models.Transaction.date >= start_of_period,
            models.Transaction.date < end_of_period,
            models.Transaction.is_transfer == False,
            models.Transaction.exclude_from_reports == False,
            models.Transaction.amount > 0
        )
        if user_id:
            total_income = total_income.join(models.Account, models.Transaction.account_id == models.Account.id).filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))
        total_income = total_income.scalar() or 0

        # Excluded
        excluded_query = db.query(func.sum(func.abs(models.Transaction.amount))).filter(
            models.Transaction.tenant_id == tenant_id,
            models.Transaction.date >= start_of_period,
            models.Transaction.date < end_of_period,
            or_(models.Transaction.exclude_from_reports == True, models.Transaction.is_transfer == True)
        )
        if user_id:
             excluded_query = excluded_query.join(models.Account, models.Transaction.account_id == models.Account.id).filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))
        total_excluded = excluded_query.scalar() or 0
        
        excluded_income_query = db.query(func.sum(models.Transaction.amount)).filter(
            models.Transaction.tenant_id == tenant_id,
            models.Transaction.date >= start_of_period,
            models.Transaction.date < end_of_period,
            or_(models.Transaction.exclude_from_reports == True, models.Transaction.is_transfer == True),
            models.Transaction.amount > 0
        )
        if user_id:
             excluded_income_query = excluded_income_query.join(models.Account, models.Transaction.account_id == models.Account.id).filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))
        excluded_income = excluded_income_query.scalar() or 0
        

        # Budget Limit
        overall_b = db.query(models.Budget).filter(
            models.Budget.tenant_id == tenant_id,
            models.Budget.category == 'OVERALL'
        ).first()
        
        limit = overall_b.amount_limit if overall_b else None
        
        return {
            "category": "OVERALL",
            "amount_limit": limit,
            "spent": total_expense,
            "income": total_income,
            "remaining": limit - total_expense if limit else None,
            "percentage": (float(total_expense) / float(limit)) * 100 if limit and limit > 0 else 0,
            "total_excluded": total_excluded,
            "excluded": total_excluded,
            "excluded_income": excluded_income,
            "updated_at": overall_b.updated_at if overall_b else None,
            "icon": "🏁",
            "color": "#10B981"
        }

    @staticmethod
    def get_budgets(db: Session, tenant_id: str, year: int = None, month: int = None, user_id: str = None) -> List[dict]:
        if user_id in [None, "null", "undefined", ""]:
            user_id = None
        """
        Get all budgets and calculate progress based on target month's spending.
        Supports hierarchical rollup (children to parents) and user/member filtering.
        """
        budgets = db.query(models.Budget).filter(models.Budget.tenant_id == tenant_id).all()
        all_categories = db.query(models.Category).filter(models.Category.tenant_id == tenant_id).all()
        
        # Build category hierarchy maps
        cat_map = {c.name: c for c in all_categories}
        children_map = {} # parent_id -> list of child names
        for c in all_categories:
            if c.parent_id:
                if c.parent_id not in children_map:
                    children_map[c.parent_id] = []
                children_map[c.parent_id].append(c.name)

        # Determine period
        now = timezone.utcnow()
        if not year: year = now.year
        if not month: month = now.month
        
        start_of_period = datetime(year, month, 1)
        if month == 12:
            end_of_period = datetime(year + 1, 1, 1)
        else:
            end_of_period = datetime(year, month + 1, 1)
        
        # Fetch raw transaction aggregates
        spending_query = db.query(
            models.Transaction.category, 
            func.sum(models.Transaction.amount).label("sum")
        ).filter(
            models.Transaction.tenant_id == tenant_id,
            models.Transaction.date >= start_of_period,
            models.Transaction.date < end_of_period,
            models.Transaction.is_transfer == False,
            models.Transaction.exclude_from_reports == False
        )
        
        if user_id:
            spending_query = spending_query.join(
                models.Account, models.Transaction.account_id == models.Account.id
            ).filter(
                or_(models.Account.owner_id == user_id, models.Account.owner_id == None)
            )

        spending_rows = spending_query.group_by(models.Transaction.category).all()
        raw_spending_map = { (row.category or 'Uncategorized'): Decimal(row.sum or 0) for row in spending_rows }
        
        # Helper for excluded spending (needed for rollups)
        excluded_query = db.query(
            models.Transaction.category,
            func.sum(models.Transaction.amount).label("sum")
        ).filter(
            models.Transaction.tenant_id == tenant_id,
            models.Transaction.date >= start_of_period,
            models.Transaction.date < end_of_period,
            or_(models.Transaction.exclude_from_reports == True, models.Transaction.is_transfer == True)
        )

        if user_id:
            excluded_query = excluded_query.join(
                models.Account, models.Transaction.account_id == models.Account.id
            ).filter(
                or_(models.Account.owner_id == user_id, models.Account.owner_id == None)
            )

        excluded_rows = excluded_query.group_by(models.Transaction.category).all()
        raw_excluded_map = { (row.category or 'Uncategorized'): Decimal(row.sum or 0) for row in excluded_rows }
        
        # Recursive Rollup Logic
        memo = {}
        def get_all_spending(cat_name):
            if cat_name in memo: return memo[cat_name]
            
            # Start with direct spending
            total_val = raw_spending_map.get(cat_name, Decimal(0))
            total_ex = raw_excluded_map.get(cat_name, Decimal(0))
            
            # Add child spending
            cat_obj = cat_map.get(cat_name)
            if cat_obj and cat_obj.id in children_map:
                for child_name in children_map[cat_obj.id]:
                    child_val, child_ex = get_all_spending(child_name)
                    total_val += child_val
                    total_ex += child_ex
            
            memo[cat_name] = (total_val, total_ex)
            return total_val, total_ex

        # Prepare Results
        budget_map = {b.category: b for b in budgets}
        results = []
        
        # Process all categories
        active_cat_names = set(cat_map.keys()) | set(raw_spending_map.keys())
        active_cat_names.discard('OVERALL')
        
        for name in sorted(list(active_cat_names)):
            b = budget_map.get(name)
            c = cat_map.get(name)
            
            # Use rolled-up figures for parent categories
            rolled_val, rolled_ex = get_all_spending(name)
            
            spent = abs(rolled_val) if rolled_val < 0 else Decimal(0)
            income = rolled_val if rolled_val > 0 else Decimal(0)
            
            limit = b.amount_limit if b else None
            remaining = limit - spent if limit else None
            percentage = (float(spent) / float(limit)) * 100 if limit and limit > 0 else 0
            
            results.append({
                "category": name,
                "amount_limit": limit,
                "spent": spent,
                "income": income,
                "excluded": abs(rolled_ex),
                "remaining": remaining,
                "percentage": percentage,
                "budget_id": b.id if b else None,
                "tenant_id": tenant_id,
                "type": c.type if c else "expense",
                "icon": c.icon if c else "🏷️",
                "color": c.color if c else "#3B82F6",
                "parent_id": c.parent_id if c else None,
                "category_id": c.id if c else None
            })
            
        return results

    @staticmethod
    def set_budget(db: Session, budget: schemas.BudgetCreate, tenant_id: str) -> models.Budget:
        # Upsert: Check if budget exists for category
        existing = db.query(models.Budget).filter(
            models.Budget.tenant_id == tenant_id,
            models.Budget.category == budget.category
        ).first()
        
        if existing:
            existing.amount_limit = budget.amount_limit
            existing.updated_at = timezone.utcnow()
            db.commit()
            db.refresh(existing)
            return existing
        else:
            new_budget = models.Budget(
                tenant_id=tenant_id,
                **budget.model_dump()
            )
            db.add(new_budget)
            db.commit()
            db.refresh(new_budget)
            return new_budget

    @staticmethod
    def delete_budget(db: Session, budget_id: str, tenant_id: str) -> bool:
        b = db.query(models.Budget).filter(models.Budget.id == budget_id, models.Budget.tenant_id == tenant_id).first()
        if not b: return False
        db.delete(b)
        db.commit()
        return True

    @staticmethod
    def get_ai_insights(db: Session, tenant_id: str, year: int = None, month: int = None, user_id: str = None) -> List[dict]:
        if user_id in [None, "null", "undefined", ""]:
            user_id = None
        """
        Gathers financial data and generates AI-driven insights/tips.
        """
        tenant_id = str(tenant_id)
        
        # Determine Periods
        now = timezone.utcnow()
        if not year: year = now.year
        if not month: month = now.month
        
        # Current Month
        start_of_current = datetime(year, month, 1)
        if month == 12:
            end_of_current = datetime(year + 1, 1, 1)
            last_month_dt = datetime(year, 11, 1)
        else:
            end_of_current = datetime(year, month + 1, 1)
            # Last Month Logic
            if month == 1:
                last_month_dt = datetime(year - 1, 12, 1)
            else:
                last_month_dt = datetime(year, month - 1, 1)

        # Fetch Current Data
        overview = BudgetService.get_budget_overview(db, tenant_id, year, month, user_id)
        data = BudgetService.get_budgets(db, tenant_id, year, month, user_id=user_id)
        
        # Fetch Last Month Data (for comparison)
        last_month_overview = BudgetService.get_budget_overview(db, tenant_id, last_month_dt.year, last_month_dt.month, user_id)
        
        # Fetch YTD Totals (Simple aggregation)
        start_of_year = datetime(year, 1, 1)
        
        ytd_query = db.query(
            func.sum(models.Transaction.amount).label("total")
        ).filter(
            models.Transaction.tenant_id == tenant_id,
            models.Transaction.date >= start_of_year,
            models.Transaction.date < end_of_current, # Up to end of current month
            models.Transaction.is_transfer == False,
            models.Transaction.exclude_from_reports == False
        )
        
        if user_id:
             ytd_query = ytd_query.join(models.Account, models.Transaction.account_id == models.Account.id).filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))
        
        ytd_expense = abs(ytd_query.filter(models.Transaction.amount < 0).scalar() or 0)
        ytd_income = ytd_query.filter(models.Transaction.amount > 0).scalar() or 0

        ytd_stats = {
            "spent": float(ytd_expense),
            "income": float(ytd_income),
            "savings_rate": ((float(ytd_income) - float(ytd_expense)) / float(ytd_income) * 100) if ytd_income > 0 else 0
        }

        # Try Gemini integration
        from backend.app.modules.ingestion.ai_service import AIService
        
        # Check if AI is configured
        ai_settings = AIService.get_settings(db, tenant_id)
        if not ai_settings or not ai_settings.get("is_enabled") or not ai_settings.get("has_api_key"):
             return [{
                "id": "setup_ai",
                "type": "info",
                "title": "Enable AI Insights",
                "content": "Configure Gemini AI in Settings to unlock personalized financial analysis.",
                "icon": "⚙️",
                "action": "settings" 
            }]

        try:
            ai_context = {
                "current_month": {
                    "overview": overview,
                    "categories": data
                },
                "last_month": {
                    "overview": last_month_overview
                },
                "ytd_stats": ytd_stats
            }
            ai_insights = AIService.generate_structured_insights(db, tenant_id, ai_context)
            if ai_insights:
                return ai_insights
        except Exception as e:
            pass

        # Fallback to hardcoded rules if AI is disabled or fails
        if not data and not overview.get("spent"):
            return [{
                "id": "intro",
                "type": "info",
                "title": "Welcome to AI Intelligence",
                "content": "Start adding transactions to get personalized financial insights.",
                "icon": "✨"
            }]

        insights = []
        overall = overview # Use the fetched overview directly
        categories = data # data is already filtered for categories


        # Overall Health
        if overall and overall["amount_limit"]:
            if overall["percentage"] > 100:
                insights.append({
                    "id": "overall_over",
                    "type": "danger",
                    "title": "Budget Breach Alert",
                    "content": f"Total spending is {overall['percentage']:.0f}% of the limit. Immediate freeze on discretionary spending recommended.",
                    "icon": "🚨"
                })
            elif overall["percentage"] > 85:
                insights.append({
                    "id": "overall_warn",
                    "type": "warning",
                    "title": "Approaching Limit",
                    "content": f"You've used {overall['percentage']:.0f}% of your total budget. Proceed with caution for the remaining days.",
                    "icon": "⚠️"
                })
            elif overall["percentage"] > 0 and overall["percentage"] < 50 and timezone.utcnow().day > 15:
                insights.append({
                    "id": "overall_good",
                    "type": "success",
                    "title": "Excellent Control",
                    "content": "Halfway through the month and less than 50% spent. You are on track for significant savings!",
                    "icon": "💎"
                })
            elif overall["percentage"] > 0:
                 insights.append({
                    "id": "overall_track",
                    "type": "info",
                    "title": "Spending on Track",
                    "content": f"Your spending is steady at {overall['percentage']:.0f}% of your budget.",
                    "icon": "👍"
                })

        # Specific Category Pain Points (Top 2 Overspent)
        overspent_cats = sorted([c for c in categories if c["amount_limit"] and c["percentage"] > 100], key=lambda x: x["percentage"], reverse=True)
        for cat in overspent_cats[:2]:
            insights.append({
                "id": f"cat_over_{cat['category']}",
                "type": "danger",
                "title": f"Drain in {cat['category']}",
                "content": f"Spending in {cat['category']} is {cat['percentage']:.0f}% of limit. Try setting a stricter limit or investigating transactions.",
                "icon": "💸"
            })

        # Top Expense (if not overspent)
        if not overspent_cats:
            top_expense = max([c for c in categories if c["spent"] > 0], key=lambda x: x["spent"], default=None)
            if top_expense:
                 insights.append({
                    "id": f"top_exp_{top_expense['category']}",
                    "type": "warning",
                    "title": f"Highest Expense: {top_expense['category']}",
                    "content": f"{top_expense['category']} accounts for the largest chunk of your spending this month.",
                    "icon": "📉"
                })

        # Under-utilized Budgets (Efficiency)
        efficient_cats = [c for c in categories if c["amount_limit"] and c["percentage"] < 50 and c["percentage"] > 0]
        if efficient_cats:
            best_saver = min(efficient_cats, key=lambda x: x["percentage"])
            insights.append({
                "id": "efficient_cat",
                "type": "success",
                "title": f"Under Budget: {best_saver['category']}",
                "content": f"Great job! You've only used {best_saver['percentage']:.0f}% of your {best_saver['category']} budget.",
                "icon": "📉"
            })

        # Income/Savings
        if ytd_stats["savings_rate"] > 20:
             insights.append({
                "id": "ytd_save",
                "type": "success",
                "title": "Strong Savings Rate",
                "content": f"Year-to-date, you're saving {ytd_stats['savings_rate']:.1f}% of your income. Keep it up!",
                "icon": "💰"
            })
        
        top_income = [c for c in categories if c["income"] > 0]
        if top_income:
            best_income = max(top_income, key=lambda x: x["income"])
            insights.append({
                "id": "income_boost",
                "type": "success",
                "title": "Positive Inflow",
                "content": f"The {best_income['category']} category contributed significantly to your cash flow.",
                "icon": "📈"
            })

        # Seasonal/General Tip (Fallback)
        if len(insights) < 3:
            insights.append({
                "id": "general_tip",
                "type": "info",
                "title": "Pro Tip: Emergency Fund",
                "content": "Aim to save at least 20% of your net income if you haven't started an emergency fund yet.",
                "icon": "🛡️"
            })

        return insights[:5] # Increased to 5
