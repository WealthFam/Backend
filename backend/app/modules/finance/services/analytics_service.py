import calendar
from decimal import Decimal
from typing import Optional
from datetime import datetime, date, timedelta, time
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, text, or_, extract
from backend.app.modules.finance import models
from backend.app.modules.finance.services.transaction_service import TransactionService
from backend.app.core import timezone
from backend.app.modules.auth import models as auth_models

class AnalyticsService:
    @staticmethod
    def get_summary_metrics(db: Session, tenant_id: str, user_role: str = "ADULT", account_id: str = None, start_date: datetime = None, end_date: datetime = None, user_id: str = None, exclude_hidden: bool = False):
        if user_id in [None, "null", "undefined", ""]:
            user_id = None
            
        if end_date:
            end_date = timezone.ensure_utc(end_date).replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Accounts & Net Worth (Accounts are filtered by owner_id if user_id is provided)
        accounts_query = db.query(models.Account).filter(models.Account.tenant_id == tenant_id)
        if user_id:
            # Show accounts owned by this user OR shared accounts (owner_id is null)
            accounts_query = accounts_query.filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))
        
        if account_id:
            accounts_query = accounts_query.filter(models.Account.id == account_id)
        if user_role == "CHILD":
            accounts_query = accounts_query.filter(models.Account.type.notin_(["INVESTMENT", "CREDIT"]))
        
        accounts = accounts_query.all()
        
        # Categorize Balances
        breakdown = {
            "net_worth": Decimal(0),
            "bank_balance": Decimal(0),
            "cash_balance": Decimal(0),
            "credit_debt": Decimal(0),
            "investment_value": Decimal(0),
            "total_credit_limit": Decimal(0),
            "available_credit": Decimal(0),
            "overall_credit_utilization": 0
        }
        
        for acc in accounts:
            bal = Decimal(acc.balance or 0)
            if acc.type == 'CREDIT_CARD':
                # For CC, positive balance means debt (liability).
                # If balance is 200, debt is 200.
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
                # Bank, Wallet, etc.
                breakdown["net_worth"] += bal
                if acc.type == 'BANK': breakdown["bank_balance"] += bal
                elif acc.type == 'WALLET': breakdown["cash_balance"] += bal

        # Calculate overall credit utilization
        if breakdown["total_credit_limit"] > 0:
            raw_overall_util = (breakdown["credit_debt"] / breakdown["total_credit_limit"]) * 100
            breakdown["overall_credit_utilization"] = float(max(Decimal(0), raw_overall_util))

        # Monthly Spending (or Filtered Spending)
        # Default to current month if no dates provided
        if not start_date and not end_date:
            today = timezone.utcnow()
            start_date = timezone.ensure_utc(datetime(today.year, today.month, 1))
            last_day = calendar.monthrange(today.year, today.month)[1]
            end_date = timezone.ensure_utc(datetime(today.year, today.month, last_day, 23, 59, 59))
        
        if start_date:
            start_date = timezone.ensure_utc(start_date).replace(hour=0, minute=0, second=0, microsecond=0)
        if end_date:
            end_date = timezone.ensure_utc(end_date).replace(hour=23, minute=59, second=59, microsecond=999999)
        monthly_spending_query = db.query(func.sum(models.Transaction.amount)).filter(
            models.Transaction.tenant_id == tenant_id,
            models.Transaction.amount < 0,
            models.Transaction.is_transfer == False,
            models.Transaction.exclude_from_reports == False
        )
        if start_date:
            monthly_spending_query = monthly_spending_query.filter(models.Transaction.date >= start_date)
        if end_date:
            monthly_spending_query = monthly_spending_query.filter(models.Transaction.date <= end_date)
        if account_id:
            monthly_spending_query = monthly_spending_query.filter(models.Transaction.account_id == account_id)
        if user_id:
            # Filter by account ownership: show user's accounts OR shared accounts (owner_id is NULL)
            monthly_spending_query = monthly_spending_query.join(
                models.Account, models.Transaction.account_id == models.Account.id
            ).filter(
                or_(models.Account.owner_id == user_id, models.Account.owner_id == None)
            )
        if user_role == "CHILD":
            monthly_spending_query = monthly_spending_query.join(models.Account, models.Transaction.account_id == models.Account.id)\
                                                           .filter(models.Account.type.notin_(["INVESTMENT", "CREDIT"]))
        
        monthly_spending = abs(Decimal(monthly_spending_query.scalar() or 0))

        # 2. Last Month Spending (Apples-to-apples comparison)
        # Default to current month if no dates provided
        now = timezone.utcnow()
        if not start_date:
            cur_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            cur_start = start_date

        last_month_start = (cur_start - timedelta(days=1)).replace(day=1)
        # To make it fair, we only count up to the same day of the month
        days_in_month = (now - cur_start).days + 1
        last_month_comparison_point = last_month_start + timedelta(days=days_in_month - 1)
        
        last_month_query = db.query(func.sum(models.Transaction.amount)).filter(
            models.Transaction.tenant_id == tenant_id,
            models.Transaction.amount < 0,
            models.Transaction.is_transfer == False,
            models.Transaction.exclude_from_reports == False,
            models.Transaction.date >= last_month_start,
            models.Transaction.date <= last_month_comparison_point
        )
        if account_id: last_month_query = last_month_query.filter(models.Transaction.account_id == account_id)
        if user_id:
            last_month_query = last_month_query.join(
                models.Account, models.Transaction.account_id == models.Account.id
            ).filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))
        
        last_month_spending = abs(Decimal(last_month_query.scalar() or 0))

        # 2a. Monthly Income
        monthly_income_query = db.query(func.sum(models.Transaction.amount)).filter(
            models.Transaction.tenant_id == tenant_id,
            models.Transaction.amount > 0,
            models.Transaction.is_transfer == False,
            models.Transaction.exclude_from_reports == False
        )
        if start_date:
            monthly_income_query = monthly_income_query.filter(models.Transaction.date >= start_date)
        if end_date:
            monthly_income_query = monthly_income_query.filter(models.Transaction.date <= end_date)
        if account_id:
            monthly_income_query = monthly_income_query.filter(models.Transaction.account_id == account_id)
        if user_id:
            monthly_income_query = monthly_income_query.join(
                models.Account, models.Transaction.account_id == models.Account.id
            ).filter(
                or_(models.Account.owner_id == user_id, models.Account.owner_id == None)
            )
        monthly_income = Decimal(monthly_income_query.scalar() or 0)
        
        # 2b. Total Excluded for the period
        def get_excluded_sum(is_income: bool):
            q = db.query(func.sum(models.Transaction.amount)).filter(
                models.Transaction.tenant_id == tenant_id,
                or_(models.Transaction.exclude_from_reports == True, models.Transaction.is_transfer == True)
            )
            if is_income: q = q.filter(models.Transaction.amount > 0)
            else: q = q.filter(models.Transaction.amount < 0)
            
            if start_date: q = q.filter(models.Transaction.date >= start_date)
            if end_date: q = q.filter(models.Transaction.date <= end_date)
            if account_id: q = q.filter(models.Transaction.account_id == account_id)
            if user_id:
                q = q.join(models.Account, models.Transaction.account_id == models.Account.id)\
                     .filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))
            return abs(Decimal(q.scalar() or 0))

        total_excluded = get_excluded_sum(False) # Expenses
        excluded_income = get_excluded_sum(True) # Incomes
        
        # Overall Budget Health
        all_budgets = db.query(models.Budget).filter(models.Budget.tenant_id == tenant_id).all()
        overall = next((b for b in all_budgets if b.category == 'OVERALL'), None)
        total_budget_limit = Decimal(overall.amount_limit) if overall else Decimal(0)
        if not overall and all_budgets:
            total_budget_limit = sum(Decimal(b.amount_limit) for b in all_budgets)
            
        budget_health = {
            "limit": total_budget_limit,
            "spent": monthly_spending,
            "percentage": float((monthly_spending / total_budget_limit * 100)) if total_budget_limit > 0 else 0.0
        }
        
        # Recent Transactions (bounded by month if dates provided)
        recent_txns = TransactionService.get_transactions(
            db, tenant_id, limit=5, 
            start_date=start_date, 
            end_date=end_date,
            user_role=user_role, user_id=user_id, 
            exclude_from_reports=exclude_hidden, 
            exclude_transfers=exclude_hidden
        )
        
        account_ids = list(set(txn.account_id for txn in recent_txns))
        accounts_with_owners = db.query(models.Account).options(joinedload(models.Account.owner)).filter(models.Account.id.in_(account_ids)).all()
        account_map = {a.id: a for a in accounts_with_owners}

        # Pre-fetch category map for efficiency
        from backend.app.modules.finance.models import Category
        category_objs = db.query(Category).filter(Category.tenant_id == tenant_id).all()
        cat_map = {c.name: c for c in category_objs}

        enriched_txns = []
        for txn in recent_txns:
            # Try exact match, then leaf name match for hierarchy (e.g. "Food › Dining" -> "Dining")
            cat_obj = cat_map.get(txn.category)
            if not cat_obj and txn.category and " › " in txn.category:
                leaf_name = txn.category.split(" › ")[-1]
                cat_obj = cat_map.get(leaf_name)
                
            # Ensure hierarchy display parity with web
            display_category = txn.category or "Uncategorized"
            if display_category and " › " not in display_category:
                cat_obj = cat_map.get(display_category)
                if cat_obj and cat_obj.parent_id:
                    parent = next((c for c in category_objs if c.id == cat_obj.parent_id), None)
                    if parent:
                        display_category = f"{parent.name} › {cat_obj.name}"

            txn_dict = {
                "id": txn.id,
                "date": txn.date,
                "description": txn.description,
                "amount": Decimal(txn.amount),
                "category": display_category,
                "category_icon": cat_obj.icon if cat_obj else "🏷️",
                "category_color": cat_obj.color if cat_obj else "#9ca3af",
                "account_id": str(txn.account_id),
                "is_transfer": txn.is_transfer,
                "exclude_from_reports": txn.exclude_from_reports,
                "expense_group_id": str(txn.expense_group_id) if txn.expense_group_id else None,
                "source": txn.source
            }
            
            account = account_map.get(txn.account_id)
            if account and account.owner:
                txn_dict["account_owner_name"] = account.owner.full_name or account.owner.email.split('@')[0]
            
            enriched_txns.append(txn_dict)

        # Top Spending Category this month
        top_cat_query = db.query(
            models.Transaction.category,
            func.sum(models.Transaction.amount).label('total')
        ).filter(
            models.Transaction.tenant_id == tenant_id,
            models.Transaction.amount < 0,
            models.Transaction.is_transfer == False,
            models.Transaction.exclude_from_reports == False
        )
        
        if start_date:
            top_cat_query = top_cat_query.filter(models.Transaction.date >= start_date)
        if end_date:
            top_cat_query = top_cat_query.filter(models.Transaction.date <= end_date)
        if user_id:
            # Filter by account ownership
            top_cat_query = top_cat_query.join(
                models.Account, models.Transaction.account_id == models.Account.id
            ).filter(
                or_(models.Account.owner_id == user_id, models.Account.owner_id == None)
            )
            
        top_cat_query = top_cat_query.group_by(models.Transaction.category).order_by(func.sum(models.Transaction.amount).asc()).first()
        
        top_spending_category = None
        if top_cat_query:
            top_spending_category = {
                "name": top_cat_query[0] or "Uncategorized",
                "amount": abs(Decimal(top_cat_query[1]))
            }
        
        # Credit Intelligence
        credit_cards = [a for a in accounts if a.type == 'CREDIT_CARD']
        credit_intelligence = []
        for card in credit_cards:
            # Use ₹100,000 as default limit if not set
            limit = float(card.credit_limit or 0)
            if limit == 0:
                limit = 100000.0
                
            intel = {
                "id": card.id,
                "name": card.name,
                "balance": Decimal(card.balance or 0),
                "limit": limit,
                "utilization": 0,
                "billing_day": int(card.billing_day) if card.billing_day else None,
                "due_day": int(card.due_day) if card.due_day else None,
                "days_until_due": None
            }
            if intel["limit"] > 0:
                # Debt is negative balance in this system
                current_debt = abs(intel["balance"]) if intel["balance"] < 0 else 0
                raw_util = (Decimal(current_debt) / Decimal(intel["limit"])) * 100
                intel["utilization"] = float(max(Decimal(0), raw_util))
            
            # Billing Cycle Logic
            last_statement_date = None
            prev_statement_date = None
            statement_balance = 0.0
            unbilled_purchases_raw = 0.0
            last_cycle_spend_raw = 0.0
            current_cycle_payments_raw = 0.0
            minimum_due = 0.0
            
            if intel["billing_day"]:
                billing_day = int(intel["billing_day"])
                today = timezone.utcnow().date()
                
                try:
                    this_month_stmt = date(today.year, today.month, billing_day)
                except ValueError:
                    last_day = calendar.monthrange(today.year, today.month)[1]
                    this_month_stmt = date(today.year, today.month, last_day)

                if today >= this_month_stmt:
                    last_statement_date = this_month_stmt
                else:
                    # Statement was last month
                    first_of_month = today.replace(day=1)
                    prev_month_end = first_of_month - timedelta(days=1)
                    try:
                        last_statement_date = date(prev_month_end.year, prev_month_end.month, billing_day)
                    except ValueError:
                         last_day = calendar.monthrange(prev_month_end.year, prev_month_end.month)[1]
                         last_statement_date = date(prev_month_end.year, prev_month_end.month, last_day)
                
                # Calculate Previous Statement Date (one month before last_statement_date)
                if last_statement_date:
                    first_of_ls_month = last_statement_date.replace(day=1)
                    prev_month_end = first_of_ls_month - timedelta(days=1)
                    try:
                        prev_statement_date = date(prev_month_end.year, prev_month_end.month, billing_day)
                    except ValueError:
                         last_day = calendar.monthrange(prev_month_end.year, prev_month_end.month)[1]
                         prev_statement_date = date(prev_month_end.year, prev_month_end.month, last_day)
            
            if last_statement_date:
                intel["last_statement_date"] = last_statement_date.isoformat()
                
                # Precise boundaries for cycles
                ls_midnight = datetime.combine(last_statement_date, time(23, 59, 59, 999999))
                ps_midnight = None
                if prev_statement_date:
                    ps_midnight = datetime.combine(prev_statement_date, time(23, 59, 59, 999999))
                
                # Current Cycle Spend (Negative Txns AFTER last statement date)
                unbilled_query = db.query(func.sum(models.Transaction.amount)).filter(
                    models.Transaction.account_id == card.id,
                    models.Transaction.date > ls_midnight,
                    models.Transaction.amount < 0,
                    models.Transaction.exclude_from_reports == False
                )
                unbilled_raw = unbilled_query.scalar()
                unbilled_purchases_raw = Decimal(unbilled_raw) if unbilled_raw else Decimal(0)

                # Current Cycle Payments (Positive Txns AFTER last statement date)
                payments_query = db.query(func.sum(models.Transaction.amount)).filter(
                    models.Transaction.account_id == card.id,
                    models.Transaction.date > ls_midnight,
                    models.Transaction.amount > 0,
                    models.Transaction.exclude_from_reports == False
                )
                payments_raw = payments_query.scalar()
                current_cycle_payments_raw = Decimal(payments_raw) if payments_raw else Decimal(0)
                
                # Previous Cycle Spend (Between PSD and LSD)
                if ps_midnight:
                    last_cycle_query = db.query(func.sum(models.Transaction.amount)).filter(
                        models.Transaction.account_id == card.id,
                        models.Transaction.date > ps_midnight,
                        models.Transaction.date <= ls_midnight,
                        models.Transaction.amount < 0,
                        models.Transaction.exclude_from_reports == False
                    )
                    last_cycle_raw = last_cycle_query.scalar()
                    last_cycle_spend_raw = Decimal(last_cycle_raw) if last_cycle_raw else Decimal(0)
                
                # Formula: StatementBalance = CurrentBalance - RecentSpend(Negative) - RecentPayments(Positive)
                statement_balance = intel["balance"] - unbilled_purchases_raw - current_cycle_payments_raw

                if statement_balance < 0:
                    minimum_due = abs(statement_balance) * Decimal("0.05")
                
                # Standardized logic complete
                pass
                    
            intel["statement_balance"] = abs(statement_balance)
            intel["unbilled_spend"] = abs(unbilled_purchases_raw)
            intel["last_cycle_spend"] = abs(last_cycle_spend_raw)
            intel["current_cycle_payments"] = abs(current_cycle_payments_raw)
            intel["minimum_due"] = abs(minimum_due)
            intel["last_bill_date"] = last_statement_date.isoformat() if last_statement_date else None

            if intel["due_day"]:
                try:
                    due_date = date(today.year, today.month, int(intel["due_day"]))
                    if due_date < today:
                         # Move to next month
                        if today.month == 12:
                            due_date = date(today.year + 1, 1, int(intel["due_day"]))
                        else:
                            due_date = date(today.year, today.month + 1, int(intel["due_day"]))
                            
                    intel["days_until_due"] = (due_date - today).days
                    intel["next_due_date"] = due_date.isoformat()
                except ValueError:
                    pass

            credit_intelligence.append(intel)


        # Calculate daily velocity
        today_date = timezone.utcnow().date()
        if start_date and start_date.date().month == today_date.month and start_date.date().year == today_date.year:
            days_run = today_date.day
        elif start_date and end_date:
            days_run = max(1, (end_date.date() - start_date.date()).days + 1)
        else:
            days_run = today_date.day
            
        avg_daily = monthly_spending / Decimal(max(1, days_run))

        return {
            "breakdown": breakdown,
            "total_income": monthly_income,
            "monthly_total": monthly_spending,
            "monthly_spending": monthly_spending,
            "avg_daily_spending": avg_daily,
            "last_month_spending": last_month_spending,
            "total_excluded": total_excluded,
            "excluded_income": excluded_income,
            "budget_health": budget_health,
            "credit_intelligence": credit_intelligence,
            "recent_transactions": enriched_txns,
            "top_spending_category": top_spending_category,
            "currency": accounts[0].currency if accounts else "INR"
        }

    @staticmethod
    def get_mobile_summary_metrics(db: Session, tenant_id: str, user_role: str = "ADULT", month: int = None, year: int = None, user_id: str = None):
        """
        Specialized aggregator for the mobile dashboard.
        Calls the core summary and enriches it with mobile-only dashboard metrics.
        """
        now = timezone.utcnow()
        target_month = month or now.month
        target_year = year or now.year
        start_date = timezone.ensure_utc(datetime(target_year, target_month, 1))
        last_day = calendar.monthrange(target_year, target_month)[1]
        end_date = timezone.ensure_utc(datetime(target_year, target_month, last_day, 23, 59, 59))
        
        # 1. Get Base Metrics
        base = AnalyticsService.get_summary_metrics(
            db, tenant_id, user_role=user_role, start_date=start_date, end_date=end_date, user_id=user_id, exclude_hidden=True
        )
        
        # 2. Add Daily Real-time Metrics (mobile-only dashboard features)
        is_current_month = (target_month == now.month and target_year == now.year)
        today_total = 0.0
        yesterday_total = 0.0
        last_month_same_day_total = 0.0
        prorated_budget = 0.0
        daily_budget_limit = base["budget_health"]["limit"] / last_day if base["budget_health"]["limit"] > 0 else 0

        if is_current_month:
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            yesterday_start = today_start - timedelta(days=1)
            yesterday_end = today_start - timedelta(microseconds=1)
            
            # Last month same day
            try:
                if now.month == 1:
                    lm_sd_start = timezone.ensure_utc(datetime(now.year - 1, 12, now.day))
                else:
                    lm_sd_start = timezone.ensure_utc(datetime(now.year, now.month - 1, now.day))
            except ValueError:
                lm_sd_start = today_start - timedelta(days=30)
            
            lm_sd_start = lm_sd_start.replace(hour=0, minute=0, second=0, microsecond=0)
            lm_sd_end = lm_sd_start.replace(hour=23, minute=59, second=59, microsecond=999999)

            def get_daily_sum(d_start, d_end):
                from backend.app.modules.finance.models import Transaction, Account
                q = db.query(func.sum(Transaction.amount)).filter(
                    Transaction.tenant_id == tenant_id,
                    Transaction.amount < 0,
                    Transaction.is_transfer == False,
                    Transaction.exclude_from_reports == False,
                    Transaction.date >= d_start,
                    Transaction.date <= d_end
                )
                if user_id:
                    q = q.join(Account, Transaction.account_id == Account.id)\
                         .filter(or_(Account.owner_id == user_id, Account.owner_id == None))
                return abs(Decimal(q.scalar() or 0))

            today_total = get_daily_sum(today_start, now)
            yesterday_total = get_daily_sum(yesterday_start, yesterday_end)
            last_month_same_day_total = get_daily_sum(lm_sd_start, lm_sd_end)
            prorated_budget = daily_budget_limit * now.day

        # 3. Latest Transaction (mobile callout)
        from backend.app.modules.finance.models import Transaction, Account
        latest_txn_query = db.query(Transaction).filter(
            Transaction.tenant_id == tenant_id,
            Transaction.amount < 0,
            Transaction.is_transfer == False,
            Transaction.exclude_from_reports == False,
            Transaction.date >= start_date,
            Transaction.date <= end_date
        )
        if user_id:
            latest_txn_query = latest_txn_query.join(Account, Transaction.account_id == Account.id)\
                                             .filter(or_(Account.owner_id == user_id, Account.owner_id == None))
        
        latest_txn = latest_txn_query.order_by(Transaction.date.desc()).first()
        latest_transaction_data = None
        if latest_txn:
            latest_transaction_data = {
                "amount": abs(float(latest_txn.amount)),
                "description": latest_txn.description,
                "time": latest_txn.date.strftime("%H:%M") if latest_txn.date else ""
            }

        return {
            **base,
            "today_total": today_total,
            "yesterday_total": yesterday_total,
            "last_month_same_day_total": last_month_same_day_total,
            "daily_budget_limit": daily_budget_limit,
            "prorated_budget": prorated_budget,
            "latest_transaction": latest_transaction_data
        }

    @staticmethod
    def get_consolidated_dashboard(db: Session, tenant_id: str, current_user, month: int = None, year: int = None, user_id: str = None):
        """
        Premium Consolidated dashboard aggregator.
        Reduces mobile round-trips to ONE (Summary + Trends + Categories + Investments + Triage).
        """
        from backend.app.modules.finance.services.mutual_funds import MutualFundService
        from backend.app.modules.finance.services.transaction_service import TransactionService
        from backend.app.modules.auth.models import User
        
        now = timezone.utcnow()
        t_month = month or now.month
        t_year = year or now.year

        # 1. Base Summary + Stats
        summary = AnalyticsService.get_mobile_summary_metrics(db, tenant_id, current_user.role, t_month, t_year, user_id)
        
        # 2. Daily + Monthly Trends
        trends = AnalyticsService.get_mobile_dashboard_trends(db, tenant_id, t_year, t_month, user_id)
        
        # 3. Category Distribution
        cats = AnalyticsService.get_mobile_dashboard_categories(db, tenant_id, t_month, t_year, user_id)
        
        # 4. Investment Summary (only for Adults)
        investment_summary = None
        if current_user.role != "CHILD":
            inv_data = MutualFundService.get_portfolio_analytics(db, tenant_id, user_id=user_id)
            if inv_data["current_value"] > 0 or inv_data["total_invested"] > 0:
                investment_summary = {
                    "total_invested": inv_data["total_invested"],
                    "current_value": inv_data["current_value"],
                    "profit_loss": inv_data.get("profit_loss", inv_data["current_value"] - inv_data["total_invested"]),
                    "xirr": inv_data["xirr"],
                    "sparkline": inv_data.get("sparkline", []),
                    "day_change": inv_data.get("day_change", 0.0),
                    "day_change_percent": inv_data.get("day_change_percent", 0.0)
                }

        # 5. Metadata Counters
        _, triage_count = TransactionService.get_pending_transactions(db, tenant_id, limit=1, user_id=user_id)
        family_members_count = db.query(User).filter(User.tenant_id == tenant_id).count()

        return {
            "summary": {
                "today_total": summary.get("today_total", 0.0),
                "yesterday_total": summary.get("yesterday_total", 0.0),
                "last_month_same_day_total": summary.get("last_month_same_day_total", 0.0),
                "monthly_total": summary.get("monthly_total", 0.0),
                "currency": summary.get("currency", "INR"),
                "daily_budget_limit": summary.get("daily_budget_limit", 0.0),
                "prorated_budget": summary.get("prorated_budget", 0.0)
            },
            "budget": summary.get("budget_health", {"limit": 0, "spent": 0, "percentage": 0}),
            **trends,
            **cats,
            "investment_summary": investment_summary,
            "recent_transactions": summary["recent_transactions"],
            "pending_triage_count": triage_count,
            "family_members_count": family_members_count
        }

    @staticmethod
    def get_mobile_summary_lightweight(db: Session, tenant_id: str, user_id: str = None):
        """Standardized lightweight metrics for mobile notifications or background tasks"""
        from backend.app.modules.finance.models import Transaction, Account
        
        # 1. Today's total spending
        today_start = timezone.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_query = db.query(func.sum(Transaction.amount)).filter(
            Transaction.tenant_id == tenant_id,
            Transaction.amount < 0,
            Transaction.is_transfer == False,
            Transaction.exclude_from_reports == False,
            Transaction.date >= today_start
        )
        
        if user_id:
            today_query = today_query.join(Account, Transaction.account_id == Account.id)\
                                     .filter(or_(Account.owner_id == user_id, Account.owner_id == None))
        
        today_total = abs(float(today_query.scalar() or 0))
        
        # 2. Month's total spending
        now = timezone.utcnow()
        month_start = timezone.ensure_utc(datetime(now.year, now.month, 1))
        month_query = db.query(func.sum(Transaction.amount)).filter(
            Transaction.tenant_id == tenant_id,
            Transaction.amount < 0,
            Transaction.is_transfer == False,
            Transaction.exclude_from_reports == False,
            Transaction.date >= month_start
        )
        
        if user_id:
            month_query = month_query.join(Account, Transaction.account_id == Account.id)\
                                     .filter(or_(Account.owner_id == user_id, Account.owner_id == None))
        
        monthly_total = abs(float(month_query.scalar() or 0))
        
        # 3. Latest transaction
        latest_query = db.query(Transaction).filter(
            Transaction.tenant_id == tenant_id,
            Transaction.amount < 0,
            Transaction.is_transfer == False,
            Transaction.exclude_from_reports == False
        )
        
        if user_id:
            latest_query = latest_query.join(Account, Transaction.account_id == Account.id)\
                                       .filter(or_(Account.owner_id == user_id, Account.owner_id == None))
        
        latest_txn = latest_query.order_by(Transaction.date.desc()).first()
        latest_transaction = None
        if latest_txn:
            latest_transaction = {
                "amount": abs(float(latest_txn.amount)),
                "description": latest_txn.description,
                "time": latest_txn.date.strftime("%H:%M") if latest_txn.date else ""
            }
        
        # 4. Budget Health
        from backend.app.modules.finance.services.budget_service import BudgetService
        today = date.today()
        budgets = BudgetService.get_budgets(db, tenant_id, today.year, today.month)
        overall = next((b for b in budgets if b['category'] == "OVERALL"), None)
        budget_health = None
        if overall:
            budget_health = {
                "percentage": float(overall['percentage']),
                "limit": float(overall['amount_limit']),
                "spent": float(overall['spent'])
            }
        
        # 5. Currency
        acc_query = db.query(Account).filter(Account.tenant_id == tenant_id)
        if user_id:
            acc_query = acc_query.filter(or_(Account.owner_id == user_id, Account.owner_id == None))
        
        first_acc = acc_query.first()
        currency = first_acc.currency if first_acc else "INR"

        return {
            "today_total": today_total,
            "monthly_total": monthly_total,
            "latest_transaction": latest_transaction,
            "budget_health": budget_health,
            "currency": currency
        }

    @staticmethod
    def get_net_worth_timeline(db: Session, tenant_id: str, days: int = 30, user_id: str = None):
        if user_id in [None, "null", "undefined", ""]:
            user_id = None
        from .mutual_funds import MutualFundService
        
        # 1. Get all accounts to track
        accounts_query = db.query(models.Account).filter(models.Account.tenant_id == tenant_id)
        if user_id:
            accounts_query = accounts_query.filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))
        accounts = accounts_query.all()
        account_ids = [str(a.id) for a in accounts]
        
        # 2. Get MF timeline (which already handles historical valuation)
        mf_res = MutualFundService.get_performance_timeline(db, tenant_id, period='1m', granularity='1d', user_id=user_id)
        mf_timeline = mf_res.get("timeline", [])
        mf_map = {datetime.fromisoformat(p["date"]).date(): p["value"] for p in mf_timeline}
        
        # 3. Reconstruct timeline day by day
        timeline = []
        now = timezone.utcnow()
        start_history = now - timedelta(days=days)
        
        # Optimization: Pre-fetch all snapshots and transactions for the period
        snapshots = db.query(models.BalanceSnapshot).filter(
            models.BalanceSnapshot.account_id.in_(account_ids),
            models.BalanceSnapshot.timestamp >= start_history - timedelta(days=1)
        ).order_by(models.BalanceSnapshot.timestamp.desc()).all()
        
        transactions = db.query(
            models.Transaction.account_id,
            func.date(models.Transaction.date).label('d'),
            func.sum(models.Transaction.amount).label('total')
        ).filter(
            models.Transaction.account_id.in_(account_ids),
            models.Transaction.date >= start_history - timedelta(days=1)
        ).group_by(models.Transaction.account_id, func.date(models.Transaction.date)).all()
        
        # {account_id: {date: total_amount}}
        txn_map = {}
        for row in transactions:
            if row.account_id not in txn_map: txn_map[row.account_id] = {}
            txn_map[row.account_id][row.d] = float(row.total)
            
        for i in range(days):
            target_date = (now - timedelta(days=i)).date()
            total_liquid = 0
            
            for acc in accounts:
                acc_id = str(acc.id)
                # Find latest snapshot ON OR BEFORE target_date
                anchor_snap = next((s for s in snapshots if s.account_id == acc_id and s.timestamp.date() <= target_date), None)
                
                if anchor_snap:
                    # Balance = Anchor + Sum(Transactions from AnchorDate+1 to TargetDate)
                    # Note: Using float for simplicity here
                    balance = float(anchor_snap.balance)
                    snap_date = anchor_snap.timestamp.date()
                    
                    # Forward track if target_date > snap_date
                    curr = snap_date + timedelta(days=1)
                    while curr <= target_date:
                        balance += txn_map.get(acc_id, {}).get(curr, 0)
                        curr += timedelta(days=1)
                else:
                    # Fallback to current balance and backtrack (original logic)
                    balance = float(acc.balance or 0)
                    curr = now.date()
                    while curr > target_date:
                        balance -= txn_map.get(acc_id, {}).get(curr, 0)
                        curr -= timedelta(days=1)
                
                if acc.type in ['BANK', 'WALLET']:
                    total_liquid += balance
                elif acc.type in ['CREDIT_CARD', 'LOAN']:
                    total_liquid -= balance
            
            mf_val = mf_map.get(target_date, 0)
            if not mf_val and mf_timeline:
                past_dates = [d for d in mf_map.keys() if d <= target_date]
                mf_val = mf_map[max(past_dates)] if past_dates else (mf_timeline[0]["value"] if mf_timeline else 0)

            timeline.append({
                "date": target_date.isoformat(),
                "liquid": round(total_liquid, 2),
                "investments": round(mf_val, 2),
                "total": round(total_liquid + mf_val, 2)
            })
            
        return timeline[::-1]


    @staticmethod
    def get_spending_trend(db: Session, tenant_id: str, user_id: str = None):
        if user_id in [None, "null", "undefined", ""]:
            user_id = None
        
        now = timezone.utcnow()
        start_date = timezone.ensure_utc(datetime(now.year, now.month, 1))

        
        # Daily spending
        query = db.query(
            func.date(models.Transaction.date).label('day'),
            func.sum(models.Transaction.amount).label('total')
        ).filter(
            models.Transaction.tenant_id == tenant_id,
            models.Transaction.date >= start_date,
            models.Transaction.amount < 0,
            models.Transaction.is_transfer == False,
            models.Transaction.exclude_from_reports == False
        )
        
        if user_id:
            # Filter by account ownership
            query = query.join(models.Account, models.Transaction.account_id == models.Account.id)\
                         .filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))
            
        spending = query.group_by(func.date(models.Transaction.date)).order_by('day').all()
        
        # Fill gaps with 0
        trend = []
        today = now.date()
        current = start_date.date()
        spend_map = {str(row.day): abs(float(row.total)) for row in spending}
        
        while current <= today:
            trend.append({
                "date": current.isoformat(),
                "amount": spend_map.get(current.isoformat(), 0.0)
            })
            current += timedelta(days=1)
            
        return trend

    @staticmethod
    def get_spending_forecast(db: Session, tenant_id: str, user_id: str = None, start_date: datetime = None, end_date: datetime = None):
        if user_id in [None, "null", "undefined", ""]:
            user_id = None
        
        now = timezone.utcnow()
        if not start_date:
            start_date = timezone.ensure_utc(datetime(now.year, now.month, 1))
        if not end_date:
            last_day = calendar.monthrange(now.year, now.month)[1]
            end_date = timezone.ensure_utc(datetime(now.year, now.month, last_day, 23, 59, 59))

        # 1. Fetch historical spending stacked by user
        query = db.query(
            func.date(models.Transaction.date).label('day'),
            models.Account.owner_id.label('user_id'),
            func.sum(models.Transaction.amount).label('total')
        ).join(models.Account, models.Transaction.account_id == models.Account.id)\
         .filter(
            models.Transaction.tenant_id == tenant_id,
            models.Transaction.date >= start_date,
            models.Transaction.date <= end_date,
            models.Transaction.date <= now, # Only historical for actuals
            models.Transaction.amount < 0,
            models.Transaction.is_transfer == False,
            models.Transaction.exclude_from_reports == False
        )
        
        if user_id:
             query = query.filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))
             
        historical_raw = query.group_by(func.date(models.Transaction.date), models.Account.owner_id).all()
        
        # 2. Smart Prediction Logic (Seasonal/Cyclical)
        # We look at patterns for each day of the month over the last ~4 months
        four_months_ago = now - timedelta(days=120)
        dom_query = db.query(
            extract('day', models.Transaction.date).label('dom'),
            func.sum(models.Transaction.amount).label('total')
        ).filter(
            models.Transaction.tenant_id == tenant_id,
            models.Transaction.date >= four_months_ago,
            models.Transaction.date < now.replace(day=1), # Complete months only
            models.Transaction.amount < 0,
            models.Transaction.is_transfer == False,
            models.Transaction.exclude_from_reports == False
        )
        if user_id:
             dom_query = dom_query.join(models.Account, models.Transaction.account_id == models.Account.id)\
                                    .filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))
        
        dom_history = dom_query.group_by(extract('day', models.Transaction.date)).all()
        # Calculate historical average for each day of the month
        dom_prediction = {int(row.dom): abs(Decimal(row.total)) / Decimal(4) for row in dom_history}
        
        # Baseline burn rate for days with no history or as a fallback
        thirty_days_ago = now - timedelta(days=30)
        burn_query = db.query(func.sum(models.Transaction.amount)).filter(
            models.Transaction.tenant_id == tenant_id,
            models.Transaction.date >= thirty_days_ago,
            models.Transaction.amount < 0,
            models.Transaction.is_transfer == False,
            models.Transaction.exclude_from_reports == False
        )
        if user_id:
             burn_query = burn_query.join(models.Account, models.Transaction.account_id == models.Account.id)\
                                    .filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))
        
        total_recent_burn = abs(Decimal(burn_query.scalar() or 0))
        daily_burn_rate = total_recent_burn / Decimal(30)
        
        # 3. Get User metadata
        users = db.query(auth_models.User).filter(auth_models.User.tenant_id == tenant_id).all()
        user_map = {str(u.id): u.full_name or u.email.split('@')[0] for u in users}
        user_map["None"] = "Shared/Other"
        
        # 4. Map historical data
        data_map = {} # {date_str: {user_id: amount}}
        for row in historical_raw:
            day_str = str(row.day)
            if day_str not in data_map: data_map[day_str] = {}
            # Use Decimal for all monetary values as per standards
            data_map[day_str][str(row.user_id) if row.user_id else "None"] = abs(Decimal(str(row.total)))
            
        # 5. Generate trend for requested range
        trend = []
        current = start_date.date()
        today = now.date()
        
        # Fetch recurring transactions once
        recs = db.query(models.RecurringTransaction).filter(
            models.RecurringTransaction.tenant_id == tenant_id,
            models.RecurringTransaction.is_active == True,
            models.RecurringTransaction.type == 'DEBIT'
        ).all()

        while current <= end_date.date():
            day_str = current.isoformat()
            day_data = {
                "date": day_str,
                "is_forecast": current > today,
                "stacks": data_map.get(day_str, {})
            }
            
            if current > today:
                # Add predicted spend: Blend (80% DOM-average, 20% recent velocity)
                dom = current.day
                dom_history_avg = dom_prediction.get(dom, daily_burn_rate)
                final_predicted = (dom_history_avg * Decimal("0.8")) + (daily_burn_rate * Decimal("0.2"))
                
                day_data["stacks"]["Predicted"] = final_predicted
                
                # Check recurring bills for this specific date (hard override/addition)
                rec_total = sum(abs(Decimal(str(r.amount))) for r in recs if r.next_run_date and r.next_run_date.date() == current)
                if rec_total > 0:
                    day_data["stacks"]["Upcoming Bills"] = rec_total

            trend.append(day_data)
            current += timedelta(days=1)
            
        # Sum up predicted values for the return
        forecast_sum = sum(
            Decimal(str(d["stacks"].get("Predicted", 0))) + Decimal(str(d["stacks"].get("Upcoming Bills", 0)))
            for d in trend if d["is_forecast"]
        )
        return {
            "user_names": user_map,
            "trend": trend,
            "daily_burn_rate": daily_burn_rate,
            "forecast_total": forecast_sum
        }

    @staticmethod
    def get_mobile_dashboard_trends(db: Session, tenant_id: str, target_year: int, target_month: int, user_id: str = None):
        """
        Deep Analysis Result: Web app uses get_spending_trend() or get_detailed_analytics().
        This specific method serves ONLY the mobile dashboard to prevent regression.
        - Truncates future dates for the current month.
        - Returns a 6-month historical overview + daily granularity for the active month.
        """
        if user_id in [None, "null", "undefined", ""]:
            user_id = None
            
        now = timezone.utcnow()
        
        # 1. Month-wise Trend (Last 6 Months centering on target_date)
        target_date = timezone.ensure_utc(datetime(target_year, target_month, 1))
        budget_history = AnalyticsService.get_budget_history(
            db, tenant_id, months=6, user_id=user_id, target_date=target_date
        )
        month_wise_trend = []
        for m in budget_history:
            overall = next((cat for cat in m["data"] if cat["category"] == "OVERALL"), None)
            if overall:
                month_wise_trend.append({"month": m["month"], "spent": overall["spent"], "budget": overall["limit"], "is_selected": m.get("is_selected", False)})
            else:
                total_spent = sum(c["spent"] for c in m["data"] if c["category"] != "OVERALL")
                total_limit = sum(c["limit"] for c in m["data"] if c["category"] != "OVERALL")
                month_wise_trend.append({"month": m["month"], "spent": total_spent, "budget": total_limit, "is_selected": m.get("is_selected", False)})

        # 2. Daily Spending Trend (Month-Bounded)
        month_start = timezone.ensure_utc(datetime(target_year, target_month, 1))
        last_day = calendar.monthrange(target_year, target_month)[1]
        month_end = timezone.ensure_utc(datetime(target_year, target_month, last_day, 23, 59, 59))
        
        # Limit query to today if it's the current month
        query_end = min(month_end, now) if month_end > now else month_end
        
        # Re-calculate daily budget limit
        metrics = AnalyticsService.get_summary_metrics(
            db, tenant_id, start_date=month_start, end_date=month_end, user_id=user_id, exclude_hidden=True
        )
        daily_limit = metrics["budget_health"]["limit"] / last_day if metrics["budget_health"]["limit"] > 0 else 0

        # Query daily totals
        from backend.app.modules.finance.models import Transaction, Account
        trend_query = db.query(
            func.date(Transaction.date).label('day'),
            func.sum(Transaction.amount).label('total')
        ).filter(
            Transaction.tenant_id == tenant_id,
            Transaction.amount < 0,
            Transaction.is_transfer == False,
            Transaction.exclude_from_reports == False,
            Transaction.date >= month_start,
            Transaction.date <= query_end
        )
        
        if user_id:
            trend_query = trend_query.join(Account, Transaction.account_id == Account.id)\
                                     .filter(or_(Account.owner_id == user_id, Account.owner_id == None))
        
        row_map = {str(row.day): abs(Decimal(row.total)) for row in trend_query.group_by(func.date(Transaction.date)).all()}
        
        # Calculate iteration limit
        days_to_show = last_day
        if target_year == now.year and target_month == now.month:
            days_to_show = now.day
        elif (target_year, target_month) > (now.year, now.month):
            days_to_show = 0

        daily_trend = []
        for i in range(days_to_show):
            curr_date = (month_start + timedelta(days=i)).date()
            d_str = curr_date.isoformat()
            daily_trend.append({
                "date": d_str,
                "amount": row_map.get(d_str, 0.0),
                "daily_limit": daily_limit
            })
            
        return {
            "month_wise_trend": month_wise_trend,
            "spending_trend": daily_trend
        }

    @staticmethod
    def get_mobile_dashboard_categories(db: Session, tenant_id: str, target_month: int, target_year: int, user_id: str = None):
        """
        Specialized category breakdown for mobile.
        Groups spending by top-level categories for the selected period.
        """
        if user_id in [None, "null", "undefined", ""]:
            user_id = None

        month_start = timezone.ensure_utc(datetime(target_year, target_month, 1))
        last_day = calendar.monthrange(target_year, target_month)[1]
        month_end = timezone.ensure_utc(datetime(target_year, target_month, last_day, 23, 59, 59))

        from backend.app.modules.finance.models import Transaction, Category, Account
        
        # 1. Fetch all expense transactions for the month
        query = db.query(Transaction).filter(
            Transaction.tenant_id == tenant_id,
            Transaction.amount < 0,
            Transaction.is_transfer == False,
            Transaction.exclude_from_reports == False,
            Transaction.date >= month_start,
            Transaction.date <= month_end
        )

        if user_id:
            query = query.join(Account, Transaction.account_id == Account.id)\
                         .filter(or_(Account.owner_id == user_id, Account.owner_id == None))

        txns = query.all()
        
        # 2. Get all categories for rollup
        db_categories = db.query(Category).filter(Category.tenant_id == tenant_id).all()
        cat_map = {c.name: c for c in db_categories}
        
        # 3. Aggregate totals
        cat_totals = {}
        for t in txns:
            cat_name = t.category or "Uncategorized"
            cat_totals[cat_name] = cat_totals.get(cat_name, Decimal(0)) + abs(Decimal(str(t.amount)))
            
        # 4. Roll up to Top-Level Categories
        rollup = {}
        for name, amount in cat_totals.items():
            cat = cat_map.get(name)
            # Find root parent
            root_name = name
            curr = cat
            while curr and curr.parent_id:
                parent = next((c for c in db_categories if c.id == curr.parent_id), None)
                if parent:
                    root_name = parent.name
                    curr = parent
                else:
                    break
            
            rollup[root_name] = rollup.get(root_name, Decimal(0)) + amount

        # 5. Format for response (Top 5 + Others)
        distribution = [{"name": k, "value": float(round(v, 2))} for k, v in rollup.items()]
        distribution.sort(key=lambda x: x["value"], reverse=True)
        
        if len(distribution) > 5:
            top_5 = distribution[:5]
            others_val = sum(Decimal(str(d["value"])) for d in distribution[5:])
            top_5.append({"name": "Others", "value": float(round(others_val, 2))})
            distribution = top_5

        return {"category_distribution": distribution}

    @staticmethod
    def get_balance_forecast(db: Session, tenant_id: str, days: int = 30, account_id: str = None, user_id: str = None):
        if user_id in [None, "null", "undefined", ""]:
            user_id = None
        
        # Starting Balance (Liquid assets only)
        liquid_accounts_query = db.query(models.Account).filter(
            models.Account.tenant_id == tenant_id,
            models.Account.type.in_(['BANK', 'WALLET'])
        )
        if account_id:
            liquid_accounts_query = liquid_accounts_query.filter(models.Account.id == account_id)
        if user_id:
            # Filter by account ownership
            liquid_accounts_query = liquid_accounts_query.filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))
        
        liquid_accounts = liquid_accounts_query.all()
        
        current_balance = sum(Decimal(acc.balance or 0) for acc in liquid_accounts)
        
        # Get Recurring Transactions
        recs_query = db.query(models.RecurringTransaction).filter(
            models.RecurringTransaction.tenant_id == tenant_id,
            models.RecurringTransaction.is_active == True
        )
        if account_id:
            recs_query = recs_query.filter(models.RecurringTransaction.account_id == account_id)
        recs = recs_query.all()
        
        # Discretionary Spending Heuristic
        thirty_days_ago = timezone.utcnow() - timedelta(days=30)
        recent_txns_query = db.query(models.Transaction).filter(
            models.Transaction.tenant_id == tenant_id,
            models.Transaction.date >= thirty_days_ago,
            models.Transaction.amount < 0,
            models.Transaction.is_transfer == False,
            models.Transaction.exclude_from_reports == False
        )
        if account_id:
            recent_txns_query = recent_txns_query.filter(models.Transaction.account_id == account_id)
        recent_txns = recent_txns_query.all()
        
        total_recent = abs(sum(Decimal(t.amount) for t in recent_txns))
        # Daily burn rate based on history
        daily_burn = total_recent / Decimal(30) if total_recent > 0 else Decimal(0)
        
        forecast = []
        today = timezone.utcnow().date()
        running_bal = current_balance
        
        for i in range(days):
            target_date = today + timedelta(days=i)
            
            # Apply burn (except for day 0)
            if i > 0:
                running_bal -= daily_burn
            
            # Apply recurring if due
            for r in recs:
                # Simplistic check: matches next_run_date or follows frequency logic
                # For this forecast, we look ahead at next_run and if it lands on this date, we apply.
                # In a more advanced version, we'd Project all occurrences in the window.
                if r.next_run_date.date() == target_date:
                    amt = Decimal(r.amount)
                    if r.type == 'DEBIT':
                        running_bal -= amt
                    else:
                        running_bal += amt
            
            forecast.append({
                "date": target_date.isoformat(),
                "balance": float(round(running_bal, 2))
            })
            
        return forecast
    @staticmethod
    def get_budget_history(db: Session, tenant_id: str, months: int = 6, user_id: str = None, target_date: datetime = None):
        if user_id in [None, "null", "undefined", ""]:
            user_id = None
            
        # Get all budgets to know which categories to track
        budgets = db.query(models.Budget).filter(models.Budget.tenant_id == tenant_id).all()
        categories = [b.category for b in budgets]
        
        # If no budgets, fallback to top 5 categories by spending in the last 6 months
        if not categories:
            top_cats_query = db.query(
                models.Transaction.category,
                func.sum(models.Transaction.amount).label('total')
            ).filter(
                models.Transaction.tenant_id == tenant_id,
                models.Transaction.amount < 0,
                models.Transaction.is_transfer == False,
                models.Transaction.exclude_from_reports == False
            )
            
            if user_id:
                 top_cats_query = top_cats_query.join(models.Account, models.Transaction.account_id == models.Account.id)\
                                                .filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))
            
            top_cats = top_cats_query.group_by(models.Transaction.category)\
                                     .order_by(func.sum(models.Transaction.amount).asc())\
                                     .limit(5).all()
            
            categories = [row.category for row in top_cats if row.category]
            if not categories:
                return []
            
            # Create dummy budget objects for the logic below
            class DummyBudget:
                def __init__(self, cat):
                    self.category = cat
                    self.amount_limit = 0
            
            budgets = [DummyBudget(c) for c in categories]

        now = timezone.utcnow()
        current_month_start = datetime(now.year, now.month, 1)

        if not target_date:
            target_date = now
            
        target_month_start = datetime(target_date.year, target_date.month, 1)
        
        # Determine End Month (Target + 2, but capped at Current)
        end_month_start = target_month_start
        for _ in range(2):
            m = end_month_start.month + 1
            y = end_month_start.year
            if m > 12:
                m = 1
                y += 1
            end_month_start = datetime(y, m, 1)
        
        if end_month_start > current_month_start:
            end_month_start = current_month_start
            
        # Start of range is 'months' before end_month_start + 1 month
        # Actually go back months-1 from end_month_start
        current_m = end_month_start.month
        current_y = end_month_start.year
        for _ in range(months - 1):
            current_m -= 1
            if current_m == 0:
                current_m = 12
                current_y -= 1
        
        start_range = datetime(current_y, current_m, 1)
        
        last_day = calendar.monthrange(end_month_start.year, end_month_start.month)[1]
        end_range_full = datetime(end_month_start.year, end_month_start.month, last_day, 23, 59, 59)

        # Query spending for ALL categories for the WHOLE period in one go
        # Group by category and month
        monthly_stats_query = db.query(
            models.Transaction.category,
            func.date_trunc('month', models.Transaction.date).label('month_start'),
            func.sum(models.Transaction.amount).label('total')
        ).filter(
            models.Transaction.tenant_id == tenant_id,
            models.Transaction.date >= start_range,
            models.Transaction.date <= end_range_full,
            models.Transaction.amount < 0,
            models.Transaction.is_transfer == False,
            models.Transaction.exclude_from_reports == False
        ).group_by(
            models.Transaction.category,
            text('month_start')
        )
        
        if user_id:
            monthly_stats_query = monthly_stats_query.join(models.Account, models.Transaction.account_id == models.Account.id)\
                                                      .filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))
            
        monthly_stats = monthly_stats_query.all()
        
        # Organize statistics into a map for easy lookup: {month_start_date: {category: amount}}
        stats_map = {}
        for row in monthly_stats:
            m_date = row.month_start.date() if hasattr(row.month_start, 'date') else row.month_start
            if m_date not in stats_map:
                stats_map[m_date] = {}
            stats_map[m_date][row.category] = abs(Decimal(row.total))
            
        # Handle 'OVERALL' special case if it exists in categories
        if 'OVERALL' in categories:
            overall_stats_query = db.query(
                func.date_trunc('month', models.Transaction.date).label('month_start'),
                func.sum(models.Transaction.amount).label('total')
            ).filter(
                models.Transaction.tenant_id == tenant_id,
                models.Transaction.date >= start_range,
                models.Transaction.date <= end_range_full,
                models.Transaction.amount < 0,
                models.Transaction.is_transfer == False,
                models.Transaction.exclude_from_reports == False
            )
            
            if user_id:
                overall_stats_query = overall_stats_query.join(models.Account, models.Transaction.account_id == models.Account.id)\
                                                          .filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))
            
            overall_stats = overall_stats_query.group_by(
                text('month_start')
            ).all()
            
            for row in overall_stats:
                m_date = row.month_start.date() if hasattr(row.month_start, 'date') else row.month_start
                if m_date not in stats_map:
                    stats_map[m_date] = {}
                stats_map[m_date]['OVERALL'] = abs(Decimal(row.total))

        history = []
        for i in range(months):
            # Calculate target month and year starting from end_month_start
            m_target = end_month_start.month - i
            y_target = end_month_start.year
            while m_target <= 0:
                m_target += 12
                y_target -= 1
            
            m_start_val = date(y_target, m_target, 1)
            month_label = m_start_val.strftime("%b %Y")
            
            entry = {
                "month": month_label,
                "is_selected": (m_target == target_date.month and y_target == target_date.year),
                "data": []
            }
            
            month_data = stats_map.get(m_start_val, {})
            for b in budgets:
                entry["data"].append({
                    "category": b.category,
                    "limit": float(b.amount_limit),
                    "spent": float(month_data.get(b.category, Decimal(0)))
                })
            
            history.append(entry)
            
        return history[::-1] # Chronological order
    @staticmethod
    def get_heatmap_data(db: Session, tenant_id: str, start_date: datetime = None, end_date: datetime = None, user_id: str = None):
        if user_id in [None, "null", "undefined", ""]:
            user_id = None
        
        if end_date:
            end_date = timezone.ensure_utc(end_date).replace(hour=23, minute=59, second=59, microsecond=999999)

        """
        Get transaction coordinates and weights for heatmap visualization.
        """
        query = db.query(
            models.Transaction.latitude,
            models.Transaction.longitude,
            models.Transaction.amount,
            models.Transaction.category,
            models.Transaction.description
        ).filter(
            models.Transaction.tenant_id == tenant_id,
            models.Transaction.latitude != None,
            models.Transaction.longitude != None,
            models.Transaction.amount < 0, # Usually want to heat up spending
            models.Transaction.exclude_from_reports == False
        )

        if start_date:
            query = query.filter(models.Transaction.date >= start_date)
        if end_date:
            query = query.filter(models.Transaction.date <= end_date)
        if user_id:
            query = query.join(models.Account, models.Transaction.account_id == models.Account.id)\
                         .filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))

        results = query.all()
        
        return [
            {
                "latitude": float(row.latitude),
                "longitude": float(row.longitude),
                "amount": float(abs(Decimal(row.amount))),
                "category": row.category,
                "description": row.description
            }
            for row in results
        ]
    @staticmethod
    def get_merchant_breakdown(db: Session, tenant_id: str, category: Optional[str] = None, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, user_id: Optional[str] = None):
        if user_id in [None, "null", "undefined", ""]:
            user_id = None
        if category in [None, "null", "undefined", "", "OVERALL"]:
            category = None
            
        if end_date:
            end_date = timezone.ensure_utc(end_date).replace(hour=23, minute=59, second=59, microsecond=999999)

        query = db.query(
            models.Transaction.recipient.label('merchant'),
            func.sum(models.Transaction.amount).label('total')
        ).filter(
            models.Transaction.tenant_id == tenant_id,
            models.Transaction.amount < 0,
            models.Transaction.is_transfer == False,
            models.Transaction.exclude_from_reports == False
        )
        
        if start_date:
            query = query.filter(models.Transaction.date >= start_date)
        if end_date:
            query = query.filter(models.Transaction.date <= end_date)
            
        if user_id:
            query = query.join(models.Account, models.Transaction.account_id == models.Account.id)\
                         .filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))
                         
        if category:
            # Hierarchical Category Filtering
            from backend.app.modules.finance.models import Category
            sub_category_names = []
            
            if category == "Uncategorized":
                query = query.filter(or_(models.Transaction.category == None, models.Transaction.category == "Uncategorized"))
            else:
                parent_cat = db.query(Category).filter(
                    Category.tenant_id == tenant_id,
                    Category.name == category,
                    Category.parent_id == None
                ).first()
                
                
                if parent_cat:
                    subs = db.query(Category).filter(Category.parent_id == parent_cat.id).all()
                    sub_category_names = [s.name for s in subs]
                
                if sub_category_names:
                    filter_list = [category] + sub_category_names
                    query = query.filter(models.Transaction.category.in_(filter_list))
                else:
                    query = query.filter(models.Transaction.category == category)

        results = query.group_by(models.Transaction.recipient).order_by(func.sum(models.Transaction.amount).asc()).all()
        
        return [
            {"merchant": row.merchant or "Unknown", "amount": float(abs(Decimal(row.total)))}
            for row in results
        ]
    @staticmethod
    def get_family_wealth(db: Session, tenant_id: str):
        # Get all users in the tenant
        from backend.app.modules.auth.models import User
        family_members = db.query(User).filter(User.tenant_id == tenant_id).all()
        
        # Get all accounts in the tenant
        accounts = db.query(models.Account).filter(models.Account.tenant_id == tenant_id).all()
        
        # Calculate breakdown
        member_wealth = []
        shared_wealth = {
            "net_worth": Decimal(0),
            "assets": Decimal(0),
            "liabilities": Decimal(0),
            "account_count": 0
        }
        
        total_assets = Decimal(0)
        total_liabilities = Decimal(0)
        
        for user in family_members:
            user_assets = Decimal(0)
            user_liabilities = Decimal(0)
            user_accounts = [a for a in accounts if a.owner_id == str(user.id)]
            
            for acc in user_accounts:
                bal = Decimal(acc.balance or 0)
                if acc.type in ['CREDIT_CARD', 'LOAN']:
                    user_liabilities += bal
                else:
                    user_assets += bal
            
            member_wealth.append({
                "user_id": str(user.id),
                "name": user.full_name or user.email.split('@')[0],
                "role": user.role,
                "net_worth": user_assets - user_liabilities,
                "assets": user_assets,
                "liabilities": user_liabilities,
                "account_count": len(user_accounts)
            })
            
            total_assets += user_assets
            total_liabilities += user_liabilities
            
        # Shared accounts (owner_id is None)
        shared_accounts = [a for a in accounts if a.owner_id is None]
        for acc in shared_accounts:
            bal = Decimal(acc.balance or 0)
            if acc.type in ['CREDIT_CARD', 'LOAN']:
                shared_wealth["liabilities"] += bal
            else:
                shared_wealth["assets"] += bal
                
        shared_wealth["net_worth"] = shared_wealth["assets"] - shared_wealth["liabilities"]
        shared_wealth["account_count"] = len(shared_accounts)
        
        total_assets += shared_wealth["assets"]
        total_liabilities += shared_wealth["liabilities"]
        
        return {
            "total_net_worth": float(total_assets - total_liabilities),
            "total_assets": float(total_assets),
            "total_liabilities": float(total_liabilities),
            "members": [
                {**m, "net_worth": float(m["net_worth"]), "assets": float(m["assets"]), "liabilities": float(m["liabilities"])}
                for m in member_wealth
            ],
            "shared": {**shared_wealth, "net_worth": float(shared_wealth["net_worth"]), "assets": float(shared_wealth["assets"]), "liabilities": float(shared_wealth["liabilities"])}
        }

    @staticmethod
    def get_detailed_analytics(db: Session, tenant_id: str, account_id: str = None, start_date: datetime = None, end_date: datetime = None, user_id: str = None, category: str = None):
        if end_date:
            end_date = timezone.ensure_utc(end_date).replace(hour=23, minute=59, second=59, microsecond=999999)

        """
        Consolidated analytics for the Dashboard/Insights view.
        Offloads heavy client-side processing to the server.
        """
        from backend.app.modules.finance.models import Transaction, Category, Account
        
        # Base filter
        filters = [
            Transaction.tenant_id == tenant_id,
            Transaction.is_transfer == False,
            Transaction.exclude_from_reports == False,
            Transaction.amount < 0
        ]
        
        if account_id:
            filters.append(Transaction.account_id == account_id)
        if start_date:
            filters.append(Transaction.date >= start_date)
        if end_date:
            filters.append(Transaction.date <= end_date)
            
        query = db.query(Transaction).filter(*filters)
        
        if user_id:
            query = query.join(Account, Transaction.account_id == Account.id)\
                         .filter(or_(Account.owner_id == user_id, Account.owner_id == None))

        # We take all relevant transactions for this period
        txns = query.all()
        
        # Category Breakdown (Hierarchical)
        db_categories = db.query(Category).filter(Category.tenant_id == tenant_id).all()
        
        cat_totals = {}
        for t in txns:
            cat_name = t.category or "Uncategorized"
            cat_totals[cat_name] = cat_totals.get(cat_name, Decimal(0)) + abs(Decimal(t.amount or 0))
            
        # Roll up children to parents
        final_categories = []
        parents = [c for c in db_categories if not c.parent_id]
        
        for p in parents:
            total = cat_totals.get(p.name, Decimal(0))
            children = [c for c in db_categories if c.parent_id == p.id]
            for c in children:
                total += cat_totals.get(c.name, Decimal(0))
            
            if total > 0:
                final_categories.append({"name": p.name, "value": float(round(total, 2))})
        
        # Top 5 + Others
        final_categories.sort(key=lambda x: x["value"], reverse=True)
        if len(final_categories) > 5:
            top_5 = final_categories[:5]
            others_val = sum(Decimal(str(c["value"])) for c in final_categories[5:])
            top_5.append({"name": "Others", "value": float(round(others_val, 2))})
            final_categories = top_5

        # Merchant Breakdown
        merc_totals = {}
        for t in txns:
            m_name = t.recipient or "Unknown"
            merc_totals[m_name] = merc_totals.get(m_name, Decimal(0)) + abs(Decimal(t.amount))
            
        final_merchants = [
            {"name": m, "value": float(round(v, 2))} 
            for m, v in merc_totals.items()
        ]
        final_merchants.sort(key=lambda x: x["value"], reverse=True)
        final_merchants = final_merchants[:6] # Top 6 merchants

        # Temporal Heatmap (Category vs Hour)
        # We only want the top categories for the heatmap grid
        active_cats = [c["name"] for c in final_categories if c["name"] != "Others"]
        heatmap_grid = {cat: {h: Decimal(0) for h in range(24)} for cat in active_cats}
        max_heat = Decimal(0)
        
        for t in txns:
            if t.category in heatmap_grid:
                hour = t.date.hour
                heatmap_grid[t.category][hour] += abs(Decimal(t.amount))
                if heatmap_grid[t.category][hour] > max_heat:
                    max_heat = heatmap_grid[t.category][hour]

        # Excluded/Shielded Transactions
        excluded_filters = [
            Transaction.tenant_id == tenant_id,
            or_(Transaction.is_transfer == True, Transaction.exclude_from_reports == True)
        ]
        if account_id: excluded_filters.append(Transaction.account_id == account_id)
        if start_date: excluded_filters.append(Transaction.date >= start_date)
        if end_date: excluded_filters.append(Transaction.date <= end_date)
        
        ex_query = db.query(Transaction).filter(*excluded_filters)
        if user_id:
            ex_query = ex_query.join(Account, Transaction.account_id == Account.id)\
                               .filter(or_(Account.owner_id == user_id, Account.owner_id == None))
        
        ex_txns = ex_query.all()
        excluded_income = sum(Decimal(t.amount) for t in ex_txns if t.amount > 0)
        excluded_expense = sum(abs(Decimal(t.amount)) for t in ex_txns if t.amount < 0)
        
        ex_cat_map = {}
        for t in ex_txns:
            cname = t.category or "Shielded"
            ex_cat_map[cname] = ex_cat_map.get(cname, Decimal(0)) + abs(Decimal(t.amount))
            
        final_ex_cats = [{"name": k, "value": float(round(v, 2))} for k, v in ex_cat_map.items()]

        # Trend Data (Daily)
        trend_filters = [
            Transaction.tenant_id == tenant_id,
            Transaction.is_transfer == False,
            Transaction.exclude_from_reports == False,
            Transaction.amount < 0
        ]
        if account_id: trend_filters.append(Transaction.account_id == account_id)
        if start_date: trend_filters.append(Transaction.date >= start_date)
        if end_date: trend_filters.append(Transaction.date <= end_date)
        
        if category:
            sub_category_names = []
            parent_cat = db.query(Category).filter(
                Category.tenant_id == tenant_id,
                Category.name == category,
                Category.parent_id == None
            ).first()
            
            if parent_cat:
                subs = db.query(Category).filter(Category.parent_id == parent_cat.id).all()
                sub_category_names = [s.name for s in subs]
            
            if sub_category_names:
                filter_list = [category] + sub_category_names
                trend_filters.append(Transaction.category.in_(filter_list))
            else:
                trend_filters.append(Transaction.category == category)
        
        trend_query = db.query(
            func.date(Transaction.date).label('day'),
            func.sum(Transaction.amount).label('total')
        ).filter(*trend_filters)
        
        if user_id:
            trend_query = trend_query.join(Account, Transaction.account_id == Account.id)\
                                     .filter(or_(Account.owner_id == user_id, Account.owner_id == None))
            
        trend_results = trend_query.group_by(func.date(Transaction.date)).order_by(func.date(Transaction.date)).all()
        final_trend = [{"date": str(r.day), "amount": float(abs(Decimal(r.total)))} for r in trend_results]

        expense_total = sum(abs(Decimal(t.amount)) for t in txns)
        income_query = db.query(func.sum(Transaction.amount)).filter(
            Transaction.tenant_id == tenant_id,
            Transaction.amount > 0,
            Transaction.is_transfer == False,
            Transaction.exclude_from_reports == False
        )
        if account_id: income_query = income_query.filter(Transaction.account_id == account_id)
        if start_date: income_query = income_query.filter(Transaction.date >= start_date)
        if end_date: income_query = income_query.filter(Transaction.date <= end_date)
        if user_id:
            income_query = income_query.join(Account, Transaction.account_id == Account.id)\
                                       .filter(or_(Account.owner_id == user_id, Account.owner_id == None))
        
        income_total = Decimal(income_query.scalar() or 0)

        # Account & Type Distributions (for AI Context)
        acc_map = {}
        type_map = {}
        for t in txns:
            aname = t.account.name if t.account else "Unknown"
            atype = t.account.type if t.account else "OTHER"
            acc_map[aname] = acc_map.get(aname, Decimal(0)) + abs(Decimal(t.amount))
            type_map[atype] = type_map.get(atype, Decimal(0)) + abs(Decimal(t.amount))
            
        final_accs = [{"name": k, "value": float(round(v, 2))} for k, v in acc_map.items()]
        final_types = [{"name": k, "value": float(round(v, 2))} for k, v in type_map.items()]

        return {
            "categories": final_categories,
            "merchants": final_merchants,
            "accounts": final_accs,
            "types": final_types,
            "heatmap": {
                "grid": {cat: {h: float(val) for h, val in hours.items()} for cat, hours in heatmap_grid.items()},
                "categories": active_cats,
                "hours": list(range(24)),
                "max": float(round(max_heat, 2))
            },
            "expense_total": float(round(expense_total, 2)),
            "income": float(round(income_total, 2)),
            "net": float(round(income_total - expense_total, 2)),
            "excludedExpense": float(round(excluded_expense, 2)),
            "excludedIncome": float(round(excluded_income, 2)),
            "excludedCategories": final_ex_cats,
            "trend": final_trend
        }

    @staticmethod
    def get_daily_spending_history(
        session: Session,
        tenant_id: str,
        user_id: str = None,
        days: int = 365,
        end_date: datetime = None
    ):
        if end_date is None:
            end_date = datetime.now()
            
        start_date = end_date - timedelta(days=days)
        """
        Returns daily spending totals for the last 'days' days.
        Used for GitHub-style calendar heatmap.
        """
        if user_id in [None, "null", "undefined", ""]:
            user_id = None
            
        from backend.app.modules.finance.models import Transaction, Account
        
        query = session.query(
            func.date(Transaction.date).label('day'),
            func.sum(Transaction.amount).label('total')
        ).filter(
            Transaction.tenant_id == tenant_id,
            Transaction.amount < 0,
            Transaction.is_transfer == False,
            Transaction.exclude_from_reports == False,
            Transaction.date >= start_date,
            Transaction.date <= end_date
        )
        
        if user_id:
            query = query.join(Account, Transaction.account_id == Account.id)\
                         .filter(or_(Account.owner_id == user_id, Account.owner_id == None))
            
        results = query.group_by(func.date(Transaction.date)).all()
        
        # Format: { "YYYY-MM-DD": amount }
        return {str(row.day): float(abs(Decimal(row.total))) for row in results}
