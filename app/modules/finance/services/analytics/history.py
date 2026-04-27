import calendar
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional

from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session

from backend.app.modules.finance import models
from backend.app.core import timezone

class HistoryAnalytics:
    @staticmethod
    def get_net_worth_timeline(db: Session, tenant_id: str, days: int = 30, user_id: str = None):
        if user_id in [None, "null", "undefined", ""]: user_id = None
        from backend.app.modules.finance.services.mutual_funds import MutualFundService
        
        accounts_query = db.query(models.Account).filter(models.Account.tenant_id == tenant_id)
        if user_id: accounts_query = accounts_query.filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))
        accounts = accounts_query.all()
        account_ids = [str(a.id) for a in accounts]
        
        mf_res = MutualFundService.get_performance_timeline(db, tenant_id, period='1m', granularity='1d', user_id=user_id)
        mf_timeline = mf_res.get("timeline", [])
        mf_map = {datetime.fromisoformat(p["date"]).date(): p["value"] for p in mf_timeline}
        
        timeline = []
        now = timezone.utcnow()
        start_history = now - timedelta(days=days)
        
        snapshots = db.query(models.BalanceSnapshot).filter(
            models.BalanceSnapshot.account_id.in_(account_ids),
            models.BalanceSnapshot.timestamp >= start_history - timedelta(days=1)
        ).order_by(models.BalanceSnapshot.timestamp.desc()).all()
        
        transactions = db.query(
            models.Transaction.account_id, func.date(models.Transaction.date).label('d'),
            func.sum(models.Transaction.amount).label('total')
        ).filter(models.Transaction.account_id.in_(account_ids), models.Transaction.date >= start_history - timedelta(days=1))\
         .group_by(models.Transaction.account_id, func.date(models.Transaction.date)).all()
        
        txn_map = {}
        for row in transactions:
            if row.account_id not in txn_map: txn_map[row.account_id] = {}
            txn_map[row.account_id][row.d] = Decimal(str(row.total))
            
        for i in range(days):
            target_date = (now - timedelta(days=i)).date()
            total_liquid = Decimal("0.0")
            for acc in accounts:
                acc_id = str(acc.id)
                anchor_snap = next((s for s in snapshots if s.account_id == acc_id and s.timestamp.date() <= target_date), None)
                if anchor_snap:
                    balance = Decimal(str(anchor_snap.balance))
                    curr = anchor_snap.timestamp.date() + timedelta(days=1)
                    while curr <= target_date:
                        balance += txn_map.get(acc_id, {}).get(curr, Decimal("0.0"))
                        curr += timedelta(days=1)
                else:
                    balance = Decimal(str(acc.balance or 0))
                    curr = now.date()
                    while curr > target_date:
                        balance -= txn_map.get(acc_id, {}).get(curr, Decimal("0.0"))
                        curr -= timedelta(days=1)
                
                if acc.type in ['BANK', 'WALLET']: total_liquid += balance
                elif acc.type in ['CREDIT_CARD', 'LOAN']: total_liquid -= balance
            
            mf_val = mf_map.get(target_date, Decimal("0.0"))
            if not mf_val and mf_timeline:
                past_dates = [d for d in mf_map.keys() if d <= target_date]
                mf_val = mf_map[max(past_dates)] if past_dates else (Decimal(str(mf_timeline[0]["value"])) if mf_timeline else Decimal("0.0"))

            timeline.append({
                "date": target_date.isoformat(),
                "liquid": round(Decimal(str(total_liquid)), 2),
                "investments": round(Decimal(str(mf_val)), 2),
                "total": round(Decimal(str(total_liquid)) + Decimal(str(mf_val)), 2)
            })
        return timeline[::-1]

    @staticmethod
    def get_budget_history(db: Session, tenant_id: str, months: int = 6, user_id: str = None, target_date: datetime = None, account_id: str = None):
        if user_id in [None, "null", "undefined", ""]: user_id = None
        budgets = db.query(models.Budget).filter(models.Budget.tenant_id == tenant_id).all()
        categories = [b.category for b in budgets]
        
        if not categories:
            # Fallback to top categories logic (simplified)
            top_cats = db.query(models.Transaction.category).filter(models.Transaction.tenant_id == tenant_id, models.Transaction.amount < 0)\
                         .group_by(models.Transaction.category).limit(5).all()
            categories = [c[0] for c in top_cats if c[0]]
            if not categories: return []
            budgets = [type('obj', (object,), {'category': c, 'amount_limit': 0}) for c in categories]

        now = timezone.utcnow()
        if not target_date: target_date = now
        end_month_start = datetime(target_date.year, target_date.month, 1)
        # Shift range for history (simplified)
        current_m, current_y = end_month_start.month, end_month_start.year
        for _ in range(months - 1):
            current_m -= 1
            if current_m == 0: current_m, current_y = 12, current_y - 1
        start_range = datetime(current_y, current_m, 1)
        last_day = calendar.monthrange(end_month_start.year, end_month_start.month)[1]
        end_range_full = datetime(end_month_start.year, end_month_start.month, last_day, 23, 59, 59)

        # Fetch category types for classification
        category_objs = db.query(models.Category).filter(models.Category.tenant_id == tenant_id).all()
        category_types = {c.name: c.type for c in category_objs}
        
        # Monthly aggregation logic with strftime for absolute consistency across drivers
        monthly_stats_query = db.query(
            models.Transaction.category,
            models.Category.name.label('cat_name'),
            models.Category.type.label('cat_type'),
            func.strftime(models.Transaction.date, '%Y-%m-01').label('month_str'),
            func.sum(models.Transaction.amount).label('total')
        ).outerjoin(models.Category, (or_(models.Transaction.category == models.Category.id, models.Transaction.category == models.Category.name)) & (models.Transaction.tenant_id == models.Category.tenant_id))\
         .filter(models.Transaction.tenant_id == tenant_id, 
                 models.Transaction.date >= start_range, 
                 models.Transaction.date <= end_range_full,
                 models.Transaction.amount < 0, 
                 models.Transaction.is_transfer == False,
                 models.Transaction.exclude_from_reports == False)\
         .group_by(models.Transaction.category, models.Category.name, models.Category.type, text('month_str'))
        
        if user_id: 
            monthly_stats_query = monthly_stats_query.join(models.Account, models.Transaction.account_id == models.Account.id)\
                                                      .filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))
        
        if account_id:
            monthly_stats_query = monthly_stats_query.filter(models.Transaction.account_id == account_id)

        monthly_stats = monthly_stats_query.all()
        stats_map = {}
        for row in monthly_stats:
            try:
                # Always convert to date object for internal map consistency
                m_date = datetime.strptime(row.month_str, '%Y-%m-%d').date()
                if m_date not in stats_map: stats_map[m_date] = {}
                
                amt = abs(Decimal(str(row.total)))
                # Map by both ID and Name to be safe
                stats_map[m_date][str(row.category)] = amt
                if row.cat_name:
                    stats_map[m_date][row.cat_name] = amt
            except Exception as e:
                print(f"Error parsing history row: {e}")

        history = []
        for i in range(months):
            # Generate each month's data
            m = start_range.month + i
            y = start_range.year + (m - 1) // 12
            m = (m - 1) % 12 + 1
            m_start = date(y, m, 1)
            
            month_data = {"month": m_start.strftime("%b %Y"), "data": []}
            total_ops_spent = Decimal(0)
            total_inv_spent = Decimal(0)
            
            # Use the already fetched results to aggregate OVERALL and INVESTMENT
            for row in monthly_stats:
                try:
                    row_date = datetime.strptime(row.month_str, '%Y-%m-%d').date()
                    if row_date == m_start:
                        amt = abs(Decimal(str(row.total)))
                        if row.cat_type == 'investment':
                            total_inv_spent += amt
                        elif row.cat_type == 'expense' or row.cat_type is None:
                            total_ops_spent += amt
                except: continue

            for b in budgets:
                spent = stats_map.get(m_start, {}).get(b.category, Decimal(0))
                month_data["data"].append({
                    "category": b.category, "limit": Decimal(b.amount_limit), "spent": spent
                })
            
            # Add or update specific aggregate entries for the frontend
            # We must be careful not to double-count if the user has a budget named exactly 'OVERALL'
            def update_or_append(cat_name, limit, spent):
                existing = next((d for d in month_data["data"] if d["category"] == cat_name), None)
                if existing:
                    existing["limit"] = limit
                    existing["spent"] = spent
                else:
                    month_data["data"].append({"category": cat_name, "limit": limit, "spent": spent})

            # Calculate OVERALL limit: If an 'OVERALL' budget exists, use it. Otherwise, sum others (excluding investment).
            overall_budget = next((b for b in budgets if b.category == "OVERALL"), None)
            if overall_budget:
                overall_limit = Decimal(overall_budget.amount_limit)
            else:
                # Fallback: Sum all budgets that are specifically 'expense' or 'None'
                overall_limit = sum(
                    Decimal(b.amount_limit) for b in budgets 
                    if b.category != "OVERALL" and (category_types.get(b.category) == "expense" or category_types.get(b.category) is None)
                )

            # Ensure "Uncategorized" spending is shown if it exists and there's no specific budget for it
            uncategorized_spent = stats_map.get(m_start, {}).get("None", Decimal(0))
            if uncategorized_spent > 0:
                update_or_append("Uncategorized", Decimal(0), uncategorized_spent)

            update_or_append("OVERALL", overall_limit, total_ops_spent)
            update_or_append("INVESTMENT", Decimal(0), total_inv_spent)
            
            history.append(month_data)
            
        return history

    @staticmethod
    def get_calendar_heatmap(db: Session, tenant_id: str, days: int = 180, user_id: str = None):
        if user_id in [None, "null", "undefined", ""]: user_id = None
        start_date = timezone.utcnow() - timedelta(days=days)
        
        query = db.query(
            func.date(models.Transaction.date).label('day'),
            func.sum(models.Transaction.amount).label('total'),
            func.count(models.Transaction.id).label('count')
        ).outerjoin(models.Category, (or_(models.Transaction.category == models.Category.id, models.Transaction.category == models.Category.name)) & (models.Transaction.tenant_id == models.Category.tenant_id))\
         .filter(models.Transaction.tenant_id == tenant_id, models.Transaction.date >= start_date,
                 models.Transaction.amount < 0, models.Transaction.is_transfer == False,
                 or_(models.Category.type == 'expense', models.Category.type == None))
        
        if user_id: query = query.join(models.Account, models.Transaction.account_id == models.Account.id)\
                                 .filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))
            
        results = query.group_by(func.date(models.Transaction.date)).all()
        return [{"date": str(row.day), "value": abs(float(row.total)), "count": int(row.count)} for row in results]

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
                "category": row.category or "Uncategorized",
                "description": row.description or "No description"
            }
            for row in results
        ]

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
