from typing import List, Optional, Dict
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, text, or_
from backend.app.modules.finance import models
from backend.app.modules.finance.services.transaction_service import TransactionService

class AnalyticsService:
    @staticmethod
    def get_summary_metrics(db: Session, tenant_id: str, user_role: str = "ADULT", account_id: str = None, start_date: datetime = None, end_date: datetime = None, user_id: str = None, exclude_hidden: bool = False):
        if user_id in [None, "null", "undefined", ""]:
            user_id = None
        
        # 1. Accounts & Net Worth (Accounts are filtered by owner_id if user_id is provided)
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
            "net_worth": 0,
            "bank_balance": 0,
            "cash_balance": 0,
            "credit_debt": 0,
            "investment_value": 0,
            "total_credit_limit": 0,
            "available_credit": 0,
            "overall_credit_utilization": 0
        }
        
        for acc in accounts:
            bal = float(acc.balance or 0)
            if acc.type == 'CREDIT_CARD':
                # For CC, positive balance means debt (liability).
                # If balance is 200, debt is 200.
                debt_amount = bal if bal > 0 else 0 
                
                breakdown["credit_debt"] += debt_amount
                # Net worth: debt reduces it.
                breakdown["net_worth"] -= bal 
                
                limit = float(acc.credit_limit or 0)
                breakdown["total_credit_limit"] += limit
                
                # Available credit: Limit - Debt. 
                # If Limit 10000, Balance 200 (Debt 200): Available = 10000 - 200 = 9800.
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
            breakdown["overall_credit_utilization"] = max(0, raw_overall_util)

        # 2. Monthly Spending (or Filtered Spending)
        # Default to current month if no dates provided
        if not start_date and not end_date:
            today = datetime.utcnow()
            start_date = datetime(today.year, today.month, 1)
            
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
        
        monthly_spending = abs(float(monthly_spending_query.scalar() or 0))

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
        monthly_income = float(monthly_income_query.scalar() or 0)
        
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
            return abs(float(q.scalar() or 0))

        total_excluded = get_excluded_sum(False) # Expenses
        excluded_income = get_excluded_sum(True) # Incomes
        
        # 3. Overall Budget Health
        all_budgets = db.query(models.Budget).filter(models.Budget.tenant_id == tenant_id).all()
        overall = next((b for b in all_budgets if b.category == 'OVERALL'), None)
        total_budget_limit = float(overall.amount_limit) if overall else 0
        if not overall and all_budgets:
            total_budget_limit = sum(float(b.amount_limit) for b in all_budgets)
            
        budget_health = {
            "limit": total_budget_limit,
            "spent": float(monthly_spending),
            "percentage": (float(monthly_spending) / total_budget_limit * 100) if total_budget_limit > 0 else 0
        }
        
        # 4. Recent Transactions (with owner names)
        recent_txns = TransactionService.get_transactions(db, tenant_id, limit=5, user_role=user_role, user_id=user_id, exclude_from_reports=exclude_hidden, exclude_transfers=exclude_hidden)
        
        # Enrich with account owner names
        enriched_txns = []
        for txn in recent_txns:
            txn_dict = {
                "id": txn.id,
                "date": txn.date,
                "description": txn.description,
                "amount": float(txn.amount),
                "category": txn.category,
                "account_id": txn.account_id,
                "is_transfer": txn.is_transfer,
                "exclude_from_reports": txn.exclude_from_reports
            }
            
            # Get account owner name
            account = db.query(models.Account).filter(models.Account.id == txn.account_id).first()
            if account and account.owner_id:
                from backend.app.modules.auth.models import User
                owner = db.query(User).filter(User.id == account.owner_id).first()
                if owner:
                    txn_dict["account_owner_name"] = owner.full_name or owner.email.split('@')[0]
            
            enriched_txns.append(txn_dict)

        # 5. Top Spending Category this month
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
                "name": top_cat_query[0],
                "amount": abs(float(top_cat_query[1]))
            }
        
        # 6. Credit Intelligence
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
                "balance": float(card.balance or 0),
                "limit": limit,
                "utilization": 0,
                "billing_day": int(card.billing_day) if card.billing_day else None,
                "due_day": int(card.due_day) if card.due_day else None,
                "days_until_due": None
            }
            if intel["limit"] > 0:
                # Calculate utilization percentage
                # Balance is positive (debt). 
                current_debt = intel["balance"] if intel["balance"] > 0 else 0
                raw_util = (current_debt / intel["limit"]) * 100
                intel["utilization"] = max(0, raw_util)
            
            # Billing Cycle Logic
            last_statement_date = None
            statement_balance = 0.0
            unbilled_purchases = 0.0
            minimum_due = 0.0
            
            if intel["billing_day"]:
                billing_day = int(intel["billing_day"])
                today = datetime.utcnow().date()
                
                # Determine Last Statement Date
                # 1. Try date in current month
                try:
                    this_month_stmt = date(today.year, today.month, billing_day)
                except ValueError:
                    # Fallback for short months (e.g. Feb)
                    import calendar
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
                         import calendar
                         last_day = calendar.monthrange(prev_month_end.year, prev_month_end.month)[1]
                         last_statement_date = date(prev_month_end.year, prev_month_end.month, last_day)
            
            if last_statement_date:
                intel["last_statement_date"] = last_statement_date.isoformat()
                
                # Calculate Unbilled Spending (Debits after statement date)
                # Note: We query DB here. For optimization in future, bulk fetch can be used.
                unbilled_query = db.query(func.sum(models.Transaction.amount)).filter(
                    models.Transaction.account_id == card.id,
                    models.Transaction.date > last_statement_date,
                    models.Transaction.amount < 0, # Debits only (Purchases)
                    models.Transaction.exclude_from_reports == False
                )
                unbilled_raw = unbilled_query.scalar()
                unbilled_purchases = float(unbilled_raw) if unbilled_raw else 0.0
                
                # Statement Balance = Current Balance - Unbilled Purchases
                # Example: Balance -25k. Unbilled -5k. Result -20k.
                # Example: Balance -25k. Unbilled 0. Result -25k.
                statement_balance = intel["balance"] - unbilled_purchases
                
                # Heuristic for Minimum Due (5% of statement balance)
                # Only if we owe money (negative)
                if statement_balance < 0:
                    minimum_due = abs(statement_balance) * 0.05
                    
            intel["statement_balance"] = statement_balance
            intel["unbilled_spend"] = abs(unbilled_purchases)
            intel["minimum_due"] = minimum_due

            if intel["due_day"]:
                today = datetime.utcnow().date() # Ensure date object
                try:
                    # If we have a last statement date, Due Date is strictly next month from that?
                    # Or same month? Usually 20-50 days grace.
                    # Simple logic: If today > due_day (this month), show next month.
                    # Better logic relative to Last Statement: Statement + ~20 days?
                    # But we maintain explicit Due Day.
                    
                    # Let's stick to "Next Due Date relative to Today"
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

        # 7. Calculate today's total spending
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_spending_query = db.query(func.sum(models.Transaction.amount)).filter(
            models.Transaction.tenant_id == tenant_id,
            models.Transaction.amount < 0,
            models.Transaction.is_transfer == False,
            models.Transaction.exclude_from_reports == False,
            models.Transaction.date >= today_start
        )
        if user_id:
            today_spending_query = today_spending_query.join(
                models.Account, models.Transaction.account_id == models.Account.id
            ).filter(
                or_(models.Account.owner_id == user_id, models.Account.owner_id == None)
            )
        today_total = abs(float(today_spending_query.scalar() or 0))
        
        # 8. Get latest transaction (most recent expense)
        latest_txn_query = db.query(models.Transaction).filter(
            models.Transaction.tenant_id == tenant_id,
            models.Transaction.amount < 0,
            models.Transaction.is_transfer == False,
            models.Transaction.exclude_from_reports == False
        )
        if user_id:
            latest_txn_query = latest_txn_query.join(
                models.Account, models.Transaction.account_id == models.Account.id
            ).filter(
                or_(models.Account.owner_id == user_id, models.Account.owner_id == None)
            )
        latest_txn = latest_txn_query.order_by(models.Transaction.date.desc()).first()
        
        latest_transaction_data = None
        if latest_txn:
            latest_transaction_data = {
                "amount": abs(float(latest_txn.amount)),
                "description": latest_txn.description,
                "time": latest_txn.date.strftime("%H:%M") if latest_txn.date else ""
            }

        return {
            "breakdown": breakdown,
            "today_total": today_total,
            "monthly_income": monthly_income,
            "monthly_total": monthly_spending,
            "monthly_spending": monthly_spending,  # Keep for backward compatibility
            "total_excluded": total_excluded,
            "excluded_income": excluded_income,
            "top_spending_category": top_spending_category,
            "budget_health": budget_health,
            "credit_intelligence": credit_intelligence,
            "recent_transactions": enriched_txns,
            "latest_transaction": latest_transaction_data,
            "currency": accounts[0].currency if accounts else "INR"
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
        now = datetime.utcnow()
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
        
        now = datetime.utcnow()
        start_date = datetime(now.year, now.month, 1)
        
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
        spend_map = {row.day: abs(float(row.total)) for row in spending}
        
        while current <= today:
            trend.append({
                "date": current.isoformat(),
                "amount": spend_map.get(current.isoformat(), 0.0)
            })
            current += timedelta(days=1)
            
        return trend

    @staticmethod
    def get_balance_forecast(db: Session, tenant_id: str, days: int = 30, account_id: str = None, user_id: str = None):
        if user_id in [None, "null", "undefined", ""]:
            user_id = None
        
        # 1. Starting Balance (Liquid assets only)
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
        
        current_balance = float(sum(acc.balance or 0 for acc in liquid_accounts))
        
        # 2. Get Recurring Transactions
        recs_query = db.query(models.RecurringTransaction).filter(
            models.RecurringTransaction.tenant_id == tenant_id,
            models.RecurringTransaction.is_active == True
        )
        if account_id:
            recs_query = recs_query.filter(models.RecurringTransaction.account_id == account_id)
        recs = recs_query.all()
        
        # 3. Discretionary Spending Heuristic
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
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
        
        total_recent = abs(sum(float(t.amount) for t in recent_txns))
        # Daily burn rate based on history
        daily_burn = total_recent / 30.0 if total_recent > 0 else 0
        
        forecast = []
        today = datetime.utcnow().date()
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
                    amt = float(r.amount)
                    if r.type == 'DEBIT':
                        running_bal -= amt
                    else:
                        running_bal += amt
            
            forecast.append({
                "date": target_date.isoformat(),
                "balance": round(running_bal, 2)
            })
            
        return forecast
    @staticmethod
    def get_budget_history(db: Session, tenant_id: str, months: int = 6, user_id: str = None):
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

        now = datetime.utcnow()
        # Calculate start of the first month in range
        first_month_offset = months - 1
        current_m = now.month
        current_y = now.year
        
        for _ in range(first_month_offset):
            current_m -= 1
            if current_m == 0:
                current_m = 12
                current_y -= 1
        
        start_range = datetime(current_y, current_m, 1)
        
        # Query spending for ALL categories for the WHOLE period in one go
        # Group by category and month
        # Note: func.date_trunc('month', ...) is supported by DuckDB
        monthly_stats_query = db.query(
            models.Transaction.category,
            func.date_trunc('month', models.Transaction.date).label('month_start'),
            func.sum(models.Transaction.amount).label('total')
        ).filter(
            models.Transaction.tenant_id == tenant_id,
            models.Transaction.date >= start_range,
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
            stats_map[m_date][row.category] = abs(float(row.total))
            
        # Handle 'OVERALL' special case if it exists in categories
        if 'OVERALL' in categories:
            overall_stats_query = db.query(
                func.date_trunc('month', models.Transaction.date).label('month_start'),
                func.sum(models.Transaction.amount).label('total')
            ).filter(
                models.Transaction.tenant_id == tenant_id,
                models.Transaction.date >= start_range,
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
                stats_map[m_date]['OVERALL'] = abs(float(row.total))

        history = []
        for i in range(months):
            # Calculate target month and year
            target_month = now.month - i
            target_year = now.year
            while target_month <= 0:
                target_month += 12
                target_year -= 1
            
            m_start = datetime(target_year, target_month, 1).date()
            month_label = m_start.strftime("%b %Y")
            
            entry = {
                "month": month_label,
                "data": []
            }
            
            month_data = stats_map.get(m_start, {})
            for b in budgets:
                entry["data"].append({
                    "category": b.category,
                    "limit": float(b.amount_limit),
                    "spent": month_data.get(b.category, 0.0)
                })
            
            history.append(entry)
            
        return history[::-1] # Chronological order
    @staticmethod
    def get_heatmap_data(db: Session, tenant_id: str, start_date: datetime = None, end_date: datetime = None, user_id: str = None):
        if user_id in [None, "null", "undefined", ""]:
            user_id = None
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
                "lat": float(row.latitude),
                "lng": float(row.longitude),
                "weight": abs(float(row.amount)),
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
            
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"DEBUG: get_merchant_breakdown - category='{category}' (type: {type(category)})")
        logger.info(f"DEBUG: get_merchant_breakdown - tenant_id='{tenant_id}', user_id='{user_id}'")

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
                logger.info("DEBUG: get_merchant_breakdown - Filtering for Uncategorized")
                query = query.filter(or_(models.Transaction.category == None, models.Transaction.category == "Uncategorized"))
            else:
                parent_cat = db.query(Category).filter(
                    Category.tenant_id == tenant_id,
                    Category.name == category,
                    Category.parent_id == None
                ).first()
                
                logger.info(f"DEBUG: get_merchant_breakdown - parent_cat found: {parent_cat.id if parent_cat else 'None'}")
                
                if parent_cat:
                    subs = db.query(Category).filter(Category.parent_id == parent_cat.id).all()
                    sub_category_names = [s.name for s in subs]
                    logger.info(f"DEBUG: get_merchant_breakdown - sub_category_names: {sub_category_names}")
                
                if sub_category_names:
                    filter_list = [category] + sub_category_names
                    logger.info(f"DEBUG: get_merchant_breakdown - Filtering by list: {filter_list}")
                    query = query.filter(models.Transaction.category.in_(filter_list))
                else:
                    logger.info(f"DEBUG: get_merchant_breakdown - Filtering by single name: '{category}'")
                    query = query.filter(models.Transaction.category == category)

        results = query.group_by(models.Transaction.recipient).order_by(func.sum(models.Transaction.amount).asc()).all()
        
        return [
            {"merchant": row.merchant or "Unknown", "amount": abs(float(row.total))}
            for row in results
        ]
    @staticmethod
    def get_family_wealth(db: Session, tenant_id: str):
        # 1. Get all users in the tenant
        from backend.app.modules.auth.models import User
        family_members = db.query(User).filter(User.tenant_id == tenant_id).all()
        
        # 2. Get all accounts in the tenant
        accounts = db.query(models.Account).filter(models.Account.tenant_id == tenant_id).all()
        
        # 3. Calculate breakdown
        member_wealth = []
        shared_wealth = {
            "net_worth": 0,
            "assets": 0,
            "liabilities": 0,
            "account_count": 0
        }
        
        total_assets = 0
        total_liabilities = 0
        
        for user in family_members:
            user_assets = 0
            user_liabilities = 0
            user_accounts = [a for a in accounts if a.owner_id == str(user.id)]
            
            for acc in user_accounts:
                bal = float(acc.balance or 0)
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
            bal = float(acc.balance or 0)
            if acc.type in ['CREDIT_CARD', 'LOAN']:
                shared_wealth["liabilities"] += bal
            else:
                shared_wealth["assets"] += bal
                
        shared_wealth["net_worth"] = shared_wealth["assets"] - shared_wealth["liabilities"]
        shared_wealth["account_count"] = len(shared_accounts)
        
        total_assets += shared_wealth["assets"]
        total_liabilities += shared_wealth["liabilities"]
        
        return {
            "total_net_worth": total_assets - total_liabilities,
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "members": member_wealth,
            "shared": shared_wealth
        }

    @staticmethod
    def get_detailed_analytics(db: Session, tenant_id: str, account_id: str = None, start_date: datetime = None, end_date: datetime = None, user_id: str = None, category: str = None):
        """
        Consolidated analytics for the Dashboard/Insights view.
        Offloads heavy client-side processing to the server.
        """
        from backend.app.modules.finance.models import Transaction, Category, Account
        
        # 1. Base filter
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
        
        # 2. Category Breakdown (Hierarchical)
        db_categories = db.query(Category).filter(Category.tenant_id == tenant_id).all()
        
        cat_totals = {}
        for t in txns:
            cat_name = t.category or "Uncategorized"
            cat_totals[cat_name] = cat_totals.get(cat_name, 0) + abs(float(t.amount))
            
        # Roll up children to parents
        final_categories = []
        parents = [c for c in db_categories if not c.parent_id]
        
        for p in parents:
            total = cat_totals.get(p.name, 0)
            children = [c for c in db_categories if c.parent_id == p.id]
            for c in children:
                total += cat_totals.get(c.name, 0)
            
            if total > 0:
                final_categories.append({"name": p.name, "value": round(total, 2)})
        
        # Top 5 + Others
        final_categories.sort(key=lambda x: x["value"], reverse=True)
        if len(final_categories) > 5:
            top_5 = final_categories[:5]
            others_val = sum(c["value"] for c in final_categories[5:])
            top_5.append({"name": "Others", "value": round(others_val, 2)})
            final_categories = top_5

        # 3. Merchant Breakdown
        merc_totals = {}
        for t in txns:
            m_name = t.recipient or "Unknown"
            merc_totals[m_name] = merc_totals.get(m_name, 0) + abs(float(t.amount))
            
        final_merchants = [
            {"name": m, "value": round(v, 2)} 
            for m, v in merc_totals.items()
        ]
        final_merchants.sort(key=lambda x: x["value"], reverse=True)
        final_merchants = final_merchants[:6] # Top 6 merchants

        # 4. Temporal Heatmap (Category vs Hour)
        # We only want the top categories for the heatmap grid
        active_cats = [c["name"] for c in final_categories if c["name"] != "Others"]
        heatmap_grid = {cat: {h: 0 for h in range(24)} for cat in active_cats}
        max_heat = 0
        
        for t in txns:
            if t.category in heatmap_grid:
                hour = t.date.hour
                heatmap_grid[t.category][hour] += abs(float(t.amount))
                if heatmap_grid[t.category][hour] > max_heat:
                    max_heat = heatmap_grid[t.category][hour]

        # 5. Excluded/Shielded Transactions
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
        excluded_income = sum(float(t.amount) for t in ex_txns if t.amount > 0)
        excluded_expense = sum(abs(float(t.amount)) for t in ex_txns if t.amount < 0)
        
        ex_cat_map = {}
        for t in ex_txns:
            cname = t.category or "Shielded"
            ex_cat_map[cname] = ex_cat_map.get(cname, 0) + abs(float(t.amount))
            
        final_ex_cats = [{"name": k, "value": round(v, 2)} for k, v in ex_cat_map.items()]

        # 6. Trend Data (Daily)
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
        final_trend = [{"date": str(r.day), "amount": abs(float(r.total))} for r in trend_results]

        expense_total = sum(abs(float(t.amount)) for t in txns)
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
        
        income_total = float(income_query.scalar() or 0)

        # 7. Account & Type Distributions (for AI Context)
        acc_map = {}
        type_map = {}
        for t in txns:
            aname = t.account.name if t.account else "Unknown"
            atype = t.account.type if t.account else "OTHER"
            acc_map[aname] = acc_map.get(aname, 0) + abs(float(t.amount))
            type_map[atype] = type_map.get(atype, 0) + abs(float(t.amount))
            
        final_accs = [{"name": k, "value": round(v, 2)} for k, v in acc_map.items()]
        final_types = [{"name": k, "value": round(v, 2)} for k, v in type_map.items()]

        return {
            "categories": final_categories,
            "merchants": final_merchants,
            "accounts": final_accs,
            "types": final_types,
            "heatmap": {
                "grid": heatmap_grid,
                "categories": active_cats,
                "hours": list(range(24)),
                "max": round(max_heat, 2)
            },
            "expense_total": round(expense_total, 2),
            "income": round(income_total, 2),
            "net": round(income_total - expense_total, 2),
            "excludedExpense": round(excluded_expense, 2),
            "excludedIncome": round(excluded_income, 2),
            "excludedCategories": final_ex_cats,
            "trend": final_trend
        }
