import calendar
from decimal import Decimal
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta, time
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, text

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

        # Monthly aggregation logic
        monthly_stats_query = db.query(
            models.Transaction.category,
            func.date_trunc('month', models.Transaction.date).label('month_start'),
            func.sum(models.Transaction.amount).label('total')
        ).outerjoin(models.Category, (or_(models.Transaction.category == models.Category.id, models.Transaction.category == models.Category.name)) & (models.Transaction.tenant_id == models.Category.tenant_id))\
         .filter(models.Transaction.tenant_id == tenant_id, models.Transaction.date >= start_range, models.Transaction.date <= end_range_full,
                 models.Transaction.amount < 0, models.Transaction.is_transfer == False,
                 or_(models.Category.type == 'expense', models.Category.type == 'investment', models.Category.type == None))\
         .group_by(models.Transaction.category, text('month_start'))
        
        if user_id: monthly_stats_query = monthly_stats_query.join(models.Account, models.Transaction.account_id == models.Account.id)\
                                                          .filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))
        
        monthly_stats = monthly_stats_query.all()
        stats_map = {}
        for row in monthly_stats:
            m_date = row.month_start.date() if hasattr(row.month_start, 'date') else row.month_start
            if m_date not in stats_map: stats_map[m_date] = {}
            stats_map[m_date][row.category] = abs(Decimal(row.total))

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
            
            # Fetch all categories for this month's stats
            for cat, amt in stats_map.get(m_start, {}).items():
                # We need to know the type of each category. 
                # This is a bit expensive to do here if we have many categories, 
                # but for budget history it's usually limited.
                # For now, let's assume if it's not a budget category, we might need a lookup or just aggregate.
                # Actually, we already filtered the query to include only expense/investment/none.
                # Let's try to find if it's an investment.
                cat_obj = db.query(models.Category).filter(
                    (models.Category.id == cat) | (models.Category.name == cat),
                    models.Category.tenant_id == tenant_id
                ).first()
                
                if cat_obj and cat_obj.type == 'investment':
                    total_inv_spent += amt
                else:
                    total_ops_spent += amt

            for b in budgets:
                spent = stats_map.get(m_start, {}).get(b.category, Decimal(0))
                month_data["data"].append({
                    "category": b.category, "limit": Decimal(b.amount_limit), "spent": spent
                })
            
            # Add specific aggregate entries for the frontend
            month_data["data"].append({
                "category": "OVERALL", "limit": sum(Decimal(b.amount_limit) for b in budgets), "spent": total_ops_spent
            })
            month_data["data"].append({
                "category": "INVESTMENT", "limit": 0, "spent": total_inv_spent
            })
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
