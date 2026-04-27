import calendar
from decimal import Decimal
from typing import Optional, Dict, Any
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, text, or_, extract

from backend.app.modules.finance import models
from backend.app.modules.finance.services.transaction_service import TransactionService
from backend.app.core import timezone
from backend.app.modules.auth import models as auth_models

class CoreAnalytics:
    @staticmethod
    def get_summary_metrics(db: Session, tenant_id: str, user_role: str = "ADULT", account_id: str = None, start_date: datetime = None, end_date: datetime = None, user_id: str = None, exclude_hidden: bool = False):
        if user_id in [None, "null", "undefined", ""]:
            user_id = None
            
        if end_date:
            end_date = timezone.ensure_utc(end_date).replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Accounts & Net Worth (Accounts are filtered by owner_id if user_id is provided)
        accounts_query = db.query(models.Account).filter(models.Account.tenant_id == tenant_id)
        if user_id:
            accounts_query = accounts_query.filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))
        
        if account_id:
            accounts_query = accounts_query.filter(models.Account.id == account_id)
        if user_role == "CHILD":
            accounts_query = accounts_query.filter(models.Account.type.notin_(["INVESTMENT", "CREDIT"]))
        
        accounts = accounts_query.all()
        
        # Categorize Balances
        breakdown = {
            "net_worth": Decimal(0), "bank_balance": Decimal(0), "cash_balance": Decimal(0),
            "credit_debt": Decimal(0), "investment_value": Decimal(0), "total_credit_limit": Decimal(0),
            "available_credit": Decimal(0), "overall_credit_utilization": 0
        }
        
        for acc in accounts:
            bal = Decimal(acc.balance or 0)
            if acc.type == 'CREDIT_CARD':
                debt_amount = bal if bal > 0 else Decimal(0) 
                breakdown["credit_debt"] += debt_amount
                breakdown["net_worth"] -= bal
                limit = Decimal(acc.credit_limit or 0)
                breakdown["total_credit_limit"] += limit
                breakdown["available_credit"] += (limit - bal)
            elif acc.type == 'INVESTMENT':
                breakdown["investment_value"] += bal
                breakdown["net_worth"] += bal
            elif acc.type == 'LOAN':
                breakdown["net_worth"] -= bal
            else:
                breakdown["net_worth"] += bal
                if acc.type == 'BANK': breakdown["bank_balance"] += bal
                elif acc.type == 'WALLET': breakdown["cash_balance"] += bal

        if breakdown["total_credit_limit"] > 0:
            raw_overall_util = (breakdown["credit_debt"] / breakdown["total_credit_limit"]) * 100
            breakdown["overall_credit_utilization"] = float(max(Decimal(0), raw_overall_util))

        # Monthly Spending (or Filtered Spending)
        if not start_date and not end_date:
            today = timezone.utcnow()
            start_date = timezone.ensure_utc(datetime(today.year, today.month, 1))
            last_day = calendar.monthrange(today.year, today.month)[1]
            end_date = timezone.ensure_utc(datetime(today.year, today.month, last_day, 23, 59, 59))
        
        if start_date:
            start_date = timezone.ensure_utc(start_date).replace(hour=0, minute=0, second=0, microsecond=0)
        if end_date:
            end_date = timezone.ensure_utc(end_date).replace(hour=23, minute=59, second=59, microsecond=999999)

        spending_base_query = db.query(func.sum(models.Transaction.amount))\
            .outerjoin(models.Category, (or_(models.Transaction.category == models.Category.id, models.Transaction.category == models.Category.name)) & (models.Transaction.tenant_id == models.Category.tenant_id))\
            .filter(
                models.Transaction.tenant_id == tenant_id,
                models.Transaction.amount < 0,
                models.Transaction.is_transfer == False,
                models.Transaction.exclude_from_reports == False,
                models.Transaction.date >= start_date,
                models.Transaction.date <= end_date
            )
        if account_id: spending_base_query = spending_base_query.filter(models.Transaction.account_id == account_id)
        if user_id:
            spending_base_query = spending_base_query.join(models.Account, models.Transaction.account_id == models.Account.id)\
                                                           .filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))
        if user_role == "CHILD":
            spending_base_query = spending_base_query.join(models.Account, models.Transaction.account_id == models.Account.id)\
                                                           .filter(models.Account.type.notin_(["INVESTMENT", "CREDIT"]))
        
        # Expenses = type 'expense' or None (uncategorized)
        monthly_spending = abs(Decimal(spending_base_query.filter(
            or_(models.Category.type == 'expense', models.Category.type == None)
        ).scalar() or 0))

        # Investment Spending = IS investment
        monthly_investment = abs(Decimal(spending_base_query.filter(
            models.Category.type == 'investment'
        ).scalar() or 0))

        # Comparison with last month
        now = timezone.utcnow()
        cur_start = start_date or now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_start = (cur_start - timedelta(days=1)).replace(day=1)
        days_in_month = (now - cur_start).days + 1
        last_month_comparison_point = last_month_start + timedelta(days=days_in_month - 1)
        
        last_month_query = db.query(func.sum(models.Transaction.amount))\
            .outerjoin(models.Category, (or_(models.Transaction.category == models.Category.id, models.Transaction.category == models.Category.name)) & (models.Transaction.tenant_id == models.Category.tenant_id))\
            .filter(
                models.Transaction.tenant_id == tenant_id,
                models.Transaction.amount < 0,
                models.Transaction.is_transfer == False,
                models.Transaction.exclude_from_reports == False,
                models.Transaction.date >= last_month_start,
                models.Transaction.date <= last_month_comparison_point,
                or_(models.Category.type == 'expense', models.Category.type == None)
            )
        if account_id: last_month_query = last_month_query.filter(models.Transaction.account_id == account_id)
        if user_id:
            last_month_query = last_month_query.join(models.Account, models.Transaction.account_id == models.Account.id)\
                                                 .filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))
        last_month_spending = abs(Decimal(last_month_query.scalar() or 0))

        # Last month investment comparison
        last_month_invest_query = db.query(func.sum(models.Transaction.amount))\
            .outerjoin(models.Category, (or_(models.Transaction.category == models.Category.id, models.Transaction.category == models.Category.name)) & (models.Transaction.tenant_id == models.Category.tenant_id))\
            .filter(
                models.Transaction.tenant_id == tenant_id,
                models.Transaction.amount < 0,
                models.Transaction.is_transfer == False,
                models.Transaction.exclude_from_reports == False,
                models.Transaction.date >= last_month_start,
                models.Transaction.date <= last_month_comparison_point,
                models.Category.type == 'investment'
            )
        if account_id: last_month_invest_query = last_month_invest_query.filter(models.Transaction.account_id == account_id)
        if user_id:
            last_month_invest_query = last_month_invest_query.join(models.Account, models.Transaction.account_id == models.Account.id)\
                                                             .filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))
        last_month_investment = abs(Decimal(last_month_invest_query.scalar() or 0))

        # Unfiltered Totals (for internal metrics like Savings Rate)
        unfiltered_spending_query = db.query(func.sum(models.Transaction.amount))\
            .outerjoin(models.Category, (or_(models.Transaction.category == models.Category.id, models.Transaction.category == models.Category.name)) & (models.Transaction.tenant_id == models.Category.tenant_id))\
            .filter(
                models.Transaction.tenant_id == tenant_id,
                models.Transaction.amount < 0,
                models.Transaction.is_transfer == False,
                models.Transaction.date >= start_date,
                models.Transaction.date <= end_date,
                or_(models.Category.type == 'expense', models.Category.type == None)
            )
        if account_id: unfiltered_spending_query = unfiltered_spending_query.filter(models.Transaction.account_id == account_id)
        if user_id:
            unfiltered_spending_query = unfiltered_spending_query.join(models.Account, models.Transaction.account_id == models.Account.id)\
                                                 .filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))
        unfiltered_spending = abs(Decimal(unfiltered_spending_query.scalar() or 0))

        unfiltered_investment_query = db.query(func.sum(models.Transaction.amount))\
            .outerjoin(models.Category, (or_(models.Transaction.category == models.Category.id, models.Transaction.category == models.Category.name)) & (models.Transaction.tenant_id == models.Category.tenant_id))\
            .filter(
                models.Transaction.tenant_id == tenant_id,
                models.Transaction.amount < 0,
                models.Transaction.is_transfer == False,
                models.Transaction.date >= start_date,
                models.Transaction.date <= end_date,
                models.Category.type == 'investment'
            )
        if account_id: unfiltered_investment_query = unfiltered_investment_query.filter(models.Transaction.account_id == account_id)
        if user_id:
            unfiltered_investment_query = unfiltered_investment_query.join(models.Account, models.Transaction.account_id == models.Account.id)\
                                                 .filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))
        unfiltered_investment = abs(Decimal(unfiltered_investment_query.scalar() or 0))

        # Monthly Income
        monthly_income_query = db.query(func.sum(models.Transaction.amount))\
            .outerjoin(models.Category, (or_(models.Transaction.category == models.Category.id, models.Transaction.category == models.Category.name)) & (models.Transaction.tenant_id == models.Category.tenant_id))\
            .filter(
                models.Transaction.tenant_id == tenant_id,
                models.Transaction.amount > 0,
                models.Transaction.is_transfer == False,
                models.Transaction.exclude_from_reports == False,
                models.Transaction.date >= start_date,
                models.Transaction.date <= end_date,
                or_(models.Category.type == 'income', models.Category.type == None)
            )
        if account_id: monthly_income_query = monthly_income_query.filter(models.Transaction.account_id == account_id)
        if user_id:
            monthly_income_query = monthly_income_query.join(models.Account, models.Transaction.account_id == models.Account.id)\
                                                 .filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))
        monthly_income = Decimal(monthly_income_query.scalar() or 0)
        
        # Unfiltered Income (including hidden for internal metrics like Savings Rate)
        unfiltered_income_query = db.query(func.sum(models.Transaction.amount))\
            .outerjoin(models.Category, (or_(models.Transaction.category == models.Category.id, models.Transaction.category == models.Category.name)) & (models.Transaction.tenant_id == models.Category.tenant_id))\
            .filter(
                models.Transaction.tenant_id == tenant_id,
                models.Transaction.amount > 0,
                models.Transaction.is_transfer == False,
                models.Transaction.date >= start_date,
                models.Transaction.date <= end_date,
                or_(models.Category.type == 'income', models.Category.type == None)
            )
        if account_id: unfiltered_income_query = unfiltered_income_query.filter(models.Transaction.account_id == account_id)
        if user_id:
            unfiltered_income_query = unfiltered_income_query.join(models.Account, models.Transaction.account_id == models.Account.id)\
                                                 .filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))
        unfiltered_income = Decimal(unfiltered_income_query.scalar() or 0)
        
        # Budget Health
        all_budgets = db.query(models.Budget).filter(models.Budget.tenant_id == tenant_id).all()
        overall = next((b for b in all_budgets if b.category == 'OVERALL'), None)
        total_budget_limit = Decimal(overall.amount_limit) if overall else sum(Decimal(b.amount_limit) for b in all_budgets)
        budget_health = {
            "limit": total_budget_limit, "spent": monthly_spending,
            "percentage": float((monthly_spending / total_budget_limit * 100)) if total_budget_limit > 0 else 0.0
        }
        
        # Recent Transactions
        recent_txns = TransactionService.get_transactions(
            db, tenant_id, limit=5, start_date=start_date, end_date=end_date,
            user_role=user_role, user_id=user_id, exclude_from_reports=exclude_hidden, exclude_transfers=exclude_hidden
        )
        
        category_objs = db.query(models.Category).filter(models.Category.tenant_id == tenant_id).all()
        cat_map = {c.name: c for c in category_objs}
        
        account_ids = list(set(txn.account_id for txn in recent_txns))
        account_map = {a.id: a for a in db.query(models.Account).options(joinedload(models.Account.owner)).filter(models.Account.id.in_(account_ids)).all()}

        enriched_txns = []
        for txn in recent_txns:
            cat_obj = cat_map.get(txn.category)
            display_category = txn.category or "Uncategorized"
            if display_category and " › " not in display_category:
                cat_obj = cat_map.get(display_category)
                if cat_obj and cat_obj.parent_id:
                    parent = next((c for c in category_objs if c.id == cat_obj.parent_id), None)
                    if parent: display_category = f"{parent.name} › {cat_obj.name}"

            txn_dict = {
                "id": txn.id, "date": txn.date, "description": txn.description, "amount": Decimal(txn.amount),
                "category": display_category, "category_icon": cat_obj.icon if cat_obj else "🏷️",
                "category_color": cat_obj.color if cat_obj else "#9ca3af", "account_id": str(txn.account_id),
                "is_transfer": txn.is_transfer, "exclude_from_reports": txn.exclude_from_reports,
                "expense_group_id": str(txn.expense_group_id) if txn.expense_group_id else None, "source": txn.source
            }
            account = account_map.get(txn.account_id)
            if account and account.owner:
                txn_dict["account_owner_name"] = account.owner.full_name or account.owner.email.split('@')[0]
            enriched_txns.append(txn_dict)

        # Top Category
        top_cat_query = db.query(models.Transaction.category, func.sum(models.Transaction.amount).label('total'))\
            .filter(models.Transaction.tenant_id == tenant_id, models.Transaction.amount < 0, models.Transaction.is_transfer == False, 
                    models.Transaction.date >= start_date, models.Transaction.date <= end_date)\
            .group_by(models.Transaction.category).order_by(func.sum(models.Transaction.amount).asc()).first()
        top_spending_category = {"name": top_cat_query[0] or "Uncategorized", "amount": abs(Decimal(top_cat_query[1]))} if top_cat_query else None
        
        # Credit Intelligence (Simplified for now, could be moved to credit.py)
        # For brevity in this split, I'll keep the core logic here or import it.
        # Let's import it from a new credit.py
        from .credit import CreditAnalytics
        credit_intelligence = CreditAnalytics.get_credit_intelligence(db, tenant_id, accounts)

        avg_daily = monthly_spending / Decimal(max(1, days_in_month))
        # Use VISIBLE metrics for savings rate to match UI and tests
        if monthly_income > 0:
            savings_rate = float(((monthly_income - monthly_spending) / monthly_income) * 100)
        else:
            savings_rate = 0.0

        return {
            "breakdown": breakdown, "total_income": float(monthly_income), "unfiltered_income": float(unfiltered_income), 
            "unfiltered_spending": float(unfiltered_spending), "unfiltered_investment": float(unfiltered_investment),
            "monthly_total": float(monthly_spending),
            "monthly_spending": float(monthly_spending), "monthly_investment": float(monthly_investment),
            "total_investment": float(monthly_investment), "avg_daily_spending": float(avg_daily),
            "last_month_spending": float(last_month_spending), "last_month_investment": float(last_month_investment),
            "budget_health": budget_health,
            "credit_intelligence": credit_intelligence, "recent_transactions": enriched_txns,
            "top_spending_category": top_spending_category, "currency": accounts[0].currency if accounts else "INR",
            "savings_rate": savings_rate
        }

    @staticmethod
    def get_mobile_summary_metrics(db: Session, tenant_id: str, user_role: str = "ADULT", month: int = None, year: int = None, user_id: str = None):
        now = timezone.utcnow()
        target_month = month or now.month
        target_year = year or now.year
        start_date = timezone.ensure_utc(datetime(target_year, target_month, 1))
        last_day = calendar.monthrange(target_year, target_month)[1]
        end_date = timezone.ensure_utc(datetime(target_year, target_month, last_day, 23, 59, 59))
        
        base = CoreAnalytics.get_summary_metrics(db, tenant_id, user_role=user_role, start_date=start_date, end_date=end_date, user_id=user_id, exclude_hidden=True)
        
        # Mobile specific enrichments
        is_current_month = (target_month == now.month and target_year == now.year)
        today_total = 0.0
        yesterday_total = 0.0
        if is_current_month:
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_query = db.query(func.sum(models.Transaction.amount)).filter(
                models.Transaction.tenant_id == tenant_id, models.Transaction.date >= today_start,
                models.Transaction.amount < 0, models.Transaction.is_transfer == False
            )
            today_total = abs(float(today_query.scalar() or 0))
            
            yesterday_start = today_start - timedelta(days=1)
            yesterday_query = db.query(func.sum(models.Transaction.amount)).filter(
                models.Transaction.tenant_id == tenant_id, models.Transaction.date >= yesterday_start,
                models.Transaction.date < today_start, models.Transaction.amount < 0, models.Transaction.is_transfer == False
            )
            yesterday_total = abs(float(yesterday_query.scalar() or 0))

        base.update({
            "today_total": today_total,
            "yesterday_total": yesterday_total,
            "monthly_total": float(base["monthly_spending"])
        })
        return base

    @staticmethod
    def get_consolidated_dashboard(db: Session, tenant_id: str, current_user, month: int = None, year: int = None, user_id: str = None):
        from backend.app.modules.finance.services.mutual_funds import MutualFundService
        from backend.app.modules.finance.services.transaction_service import TransactionService
        from .spending import SpendingAnalytics
        
        now = timezone.utcnow()
        t_month, t_year = month or now.month, year or now.year
        summary = CoreAnalytics.get_mobile_summary_metrics(db, tenant_id, current_user.role, t_month, t_year, user_id)
        trends = SpendingAnalytics.get_mobile_dashboard_trends(db, tenant_id, t_year, t_month, user_id)
        cats = SpendingAnalytics.get_mobile_dashboard_categories(db, tenant_id, t_month, t_year, user_id)
        
        investment_summary = None
        if current_user.role != "CHILD":
            inv_data = MutualFundService.get_portfolio_analytics(db, tenant_id, user_id=user_id)
            if inv_data["current_value"] > 0 or inv_data["total_invested"] > 0:
                investment_summary = {
                    "total_invested": inv_data["total_invested"], "current_value": inv_data["current_value"],
                    "profit_loss": inv_data.get("profit_loss", inv_data["current_value"] - inv_data["total_invested"]),
                    "xirr": inv_data["xirr"], "sparkline": inv_data.get("sparkline", []),
                    "day_change": inv_data.get("day_change", 0.0), "day_change_percent": inv_data.get("day_change_percent", 0.0)
                }
        _, triage_count = TransactionService.get_pending_transactions(db, tenant_id, limit=1, user_id=user_id)
        family_members_count = db.query(auth_models.User).filter(auth_models.User.tenant_id == tenant_id).count()

        return {
            "summary": {
                "today_total": summary.get("today_total", 0.0), "yesterday_total": summary.get("yesterday_total", 0.0),
                "monthly_total": summary.get("monthly_total", 0.0), "monthly_investment": summary.get("monthly_investment", 0.0),
                "monthly_income": summary.get("monthly_income", 0.0), "currency": summary.get("currency", "INR")
            },
            "budget": summary.get("budget_health", {"limit": 0, "spent": 0, "percentage": 0}),
            **trends, **cats, "investment_summary": investment_summary,
            "recent_transactions": summary["recent_transactions"],
            "pending_triage_count": triage_count, "family_members_count": family_members_count
        }

    @staticmethod
    def get_mobile_summary_lightweight(db: Session, tenant_id: str, user_id: str = None):
        from .spending import SpendingAnalytics
        from backend.app.modules.finance.services.budget_service import BudgetService
        now = timezone.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = timezone.ensure_utc(datetime(now.year, now.month, 1))
        
        today_total = abs(Decimal(db.query(func.sum(models.Transaction.amount)).filter(
            models.Transaction.tenant_id == tenant_id, models.Transaction.date >= today_start,
            models.Transaction.amount < 0, models.Transaction.is_transfer == False
        ).scalar() or 0))
        
        monthly_total = abs(Decimal(db.query(func.sum(models.Transaction.amount)).filter(
            models.Transaction.tenant_id == tenant_id, models.Transaction.date >= month_start,
            models.Transaction.amount < 0, models.Transaction.is_transfer == False
        ).scalar() or 0))
        
        latest_txn = db.query(models.Transaction).filter(
            models.Transaction.tenant_id == tenant_id, models.Transaction.amount < 0, models.Transaction.is_transfer == False
        ).order_by(models.Transaction.date.desc()).first()
        
        budgets = BudgetService.get_budgets(db, tenant_id, now.year, now.month)
        overall = next((b for b in budgets if b['category'] == "OVERALL"), None)
        
        return {
            "today_total": today_total, "monthly_total": monthly_total,
            "latest_transaction": {"amount": abs(float(latest_txn.amount)), "description": latest_txn.description} if latest_txn else None,
            "budget_health": {"percentage": Decimal(str(overall['percentage'])), "limit": Decimal(str(overall['amount_limit'])), "spent": Decimal(str(overall['spent']))} if overall else None
        }

    @staticmethod
    def get_balance_forecast(db: Session, tenant_id: str, days: int = 30, account_id: str = None, user_id: str = None):
        if user_id in [None, "null", "undefined", ""]: user_id = None
        liquid_accounts = db.query(models.Account).filter(models.Account.tenant_id == tenant_id, models.Account.type.in_(['BANK', 'WALLET']))
        if account_id: liquid_accounts = liquid_accounts.filter(models.Account.id == account_id)
        if user_id: liquid_accounts = liquid_accounts.filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))
        liquid_accounts = liquid_accounts.all()
        
        current_balance = sum(Decimal(acc.balance or 0) for acc in liquid_accounts)
        recs = db.query(models.RecurringTransaction).filter(models.RecurringTransaction.tenant_id == tenant_id, models.RecurringTransaction.is_active == True).all()
        
        forecast = []
        today = timezone.utcnow().date()
        running_bal = current_balance
        for i in range(days):
            target_date = today + timedelta(days=i)
            # Simplistic burn/recurring logic
            for r in recs:
                if r.next_run_date and r.next_run_date.date() == target_date:
                    running_bal += Decimal(r.amount) if r.type == 'CREDIT' else -Decimal(r.amount)
            forecast.append({"date": target_date.isoformat(), "balance": float(round(running_bal, 2))})
        return forecast

