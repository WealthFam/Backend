import calendar
from decimal import Decimal
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, extract

from backend.app.modules.finance import models
from backend.app.core import timezone
from backend.app.modules.auth import models as auth_models

class SpendingAnalytics:
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
            func.sum(models.Transaction.amount).label('total')
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

        return {
            "categories": final_categories,
            "merchants": final_merchants,
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
    def get_spending_trend(db: Session, tenant_id: str, user_id: str = None):
        now = timezone.utcnow()
        start_date = timezone.ensure_utc(datetime(now.year, now.month, 1))
        
        query = db.query(
            func.date(models.Transaction.date).label('day'),
            func.sum(models.Transaction.amount).label('total')
        ).outerjoin(models.Category, (or_(models.Transaction.category == models.Category.id, models.Transaction.category == models.Category.name)) & (models.Transaction.tenant_id == models.Category.tenant_id))\
         .filter(
            models.Transaction.tenant_id == tenant_id,
            models.Transaction.date >= start_date,
            models.Transaction.amount < 0,
            models.Transaction.is_transfer == False,
            models.Transaction.exclude_from_reports == False,
            or_(models.Category.type == 'expense', models.Category.type == None)
        )
        
        if user_id:
            query = query.join(models.Account, models.Transaction.account_id == models.Account.id)\
                         .filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))
            
        spending = query.group_by(func.date(models.Transaction.date)).order_by('day').all()
        
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
    def get_merchant_breakdown(db: Session, tenant_id: str, user_id: str = None):
        now = timezone.utcnow()
        start_date = timezone.ensure_utc(datetime(now.year, now.month, 1))
        
        query = db.query(
            models.Transaction.description,
            func.sum(models.Transaction.amount).label('total'),
            func.count(models.Transaction.id).label('count')
        ).outerjoin(models.Category, (or_(models.Transaction.category == models.Category.id, models.Transaction.category == models.Category.name)) & (models.Transaction.tenant_id == models.Category.tenant_id))\
         .filter(
            models.Transaction.tenant_id == tenant_id,
            models.Transaction.date >= start_date,
            models.Transaction.amount < 0,
            models.Transaction.is_transfer == False,
            models.Transaction.exclude_from_reports == False,
            or_(models.Category.type == 'expense', models.Category.type == None)
        )
        
        if user_id:
            query = query.join(models.Account, models.Transaction.account_id == models.Account.id)\
                         .filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))
            
        results = query.group_by(models.Transaction.description).order_by(func.sum(models.Transaction.amount).asc()).limit(10).all()
        
        return [{
            "merchant": row.description or "Unknown",
            "amount": abs(Decimal(row.total)),
            "count": row.count
        } for row in results]

    @staticmethod
    def get_mobile_dashboard_trends(db: Session, tenant_id: str, target_year: int, target_month: int, user_id: str = None):
        if user_id in [None, "null", "undefined", ""]: user_id = None
        
        month_start = timezone.ensure_utc(datetime(target_year, target_month, 1))
        last_day = calendar.monthrange(target_year, target_month)[1]
        month_end = timezone.ensure_utc(datetime(target_year, target_month, last_day, 23, 59, 59))

        # Daily spending for sparkline
        query = db.query(
            func.date(models.Transaction.date).label('day'),
            func.sum(models.Transaction.amount).label('total')
        ).outerjoin(models.Category, (or_(models.Transaction.category == models.Category.id, models.Transaction.category == models.Category.name)) & (models.Transaction.tenant_id == models.Category.tenant_id))\
         .filter(models.Transaction.tenant_id == tenant_id, models.Transaction.date >= month_start, models.Transaction.date <= month_end,
                 models.Transaction.amount < 0, models.Transaction.is_transfer == False,
                 or_(models.Category.type == 'expense', models.Category.type == None))
        
        if user_id: query = query.join(models.Account, models.Transaction.account_id == models.Account.id)\
                                 .filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))
            
        spending = query.group_by(func.date(models.Transaction.date)).order_by('day').all()
        
        sparkline = []
        curr = month_start.date()
        spend_map = {str(row.day): abs(float(row.total)) for row in spending}
        while curr <= month_end.date():
            sparkline.append(spend_map.get(str(curr), 0.0))
            curr += timedelta(days=1)
            
        return {"spending_sparkline": sparkline}

    @staticmethod
    def get_mobile_dashboard_categories(db: Session, tenant_id: str, target_month: int, target_year: int, user_id: str = None):
        if user_id in [None, "null", "undefined", ""]: user_id = None
        month_start = timezone.ensure_utc(datetime(target_year, target_month, 1))
        last_day = calendar.monthrange(target_year, target_month)[1]
        month_end = timezone.ensure_utc(datetime(target_year, target_month, last_day, 23, 59, 59))

        query = db.query(models.Transaction)\
            .outerjoin(models.Category, (or_(models.Transaction.category == models.Category.id, models.Transaction.category == models.Category.name)) & (models.Transaction.tenant_id == models.Category.tenant_id))\
            .filter(models.Transaction.tenant_id == tenant_id, models.Transaction.amount < 0, models.Transaction.is_transfer == False,
                    models.Transaction.date >= month_start, models.Transaction.date <= month_end,
                    or_(models.Category.type == 'expense', models.Category.type == None))

        if user_id: query = query.join(models.Account, models.Transaction.account_id == models.Account.id)\
                                 .filter(or_(models.Account.owner_id == user_id, models.Account.owner_id == None))

        txns = query.all()
        db_categories = db.query(models.Category).filter(models.Category.tenant_id == tenant_id).all()
        cat_map = {c.name: c for c in db_categories}
        
        rollup = {}
        for t in txns:
            name = t.category or "Uncategorized"
            cat = cat_map.get(name)
            root_name = name
            curr = cat
            while curr and curr.parent_id:
                parent = next((c for c in db_categories if c.id == curr.parent_id), None)
                if parent: root_name, curr = parent.name, parent
                else: break
            rollup[root_name] = rollup.get(root_name, Decimal(0)) + abs(Decimal(str(t.amount)))

        distribution = [{"name": k, "value": float(round(v, 2))} for k, v in rollup.items()]
        distribution.sort(key=lambda x: x["value"], reverse=True)
        if len(distribution) > 5:
            top_5 = distribution[:5]
            others_val = sum(Decimal(str(d["value"])) for d in distribution[5:])
            top_5.append({"name": "Others", "value": float(round(others_val, 2))})
            distribution = top_5
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

        return {"category_distribution": distribution}

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
