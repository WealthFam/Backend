import calendar
from decimal import Decimal
from typing import List, Dict, Any
from datetime import datetime, date, timedelta, time
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.modules.finance import models
from backend.app.core import timezone

class CreditAnalytics:
    @staticmethod
    def get_credit_intelligence(db: Session, tenant_id: str, accounts: List[models.Account]) -> List[Dict[str, Any]]:
        credit_cards = [a for a in accounts if a.type == 'CREDIT_CARD']
        credit_intelligence = []
        
        for card in credit_cards:
            limit = float(card.credit_limit or 0)
            if limit == 0: limit = 100000.0 # Default limit
                
            intel = {
                "id": card.id, "name": card.name, "balance": Decimal(card.balance or 0),
                "limit": limit, "utilization": 0,
                "billing_day": int(card.billing_day) if card.billing_day else None,
                "due_day": int(card.due_day) if card.due_day else None,
                "days_until_due": None
            }
            if intel["limit"] > 0:
                # In this system, debt for CREDIT_CARD and LOAN is stored as a POSITIVE balance.
                current_debt = intel["balance"] if intel["balance"] > 0 else Decimal(0)
                raw_util = (Decimal(current_debt) / Decimal(intel["limit"])) * 100
                intel["utilization"] = float(max(Decimal(0), raw_util))
            
            # Billing Cycle Logic
            last_statement_date = None
            prev_statement_date = None
            statement_balance = Decimal(0)
            unbilled_purchases_raw = Decimal(0)
            last_cycle_spend_raw = Decimal(0)
            current_cycle_payments_raw = Decimal(0)
            minimum_due = Decimal(0)
            
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
                    first_of_month = today.replace(day=1)
                    prev_month_end = first_of_month - timedelta(days=1)
                    try:
                        last_statement_date = date(prev_month_end.year, prev_month_end.month, billing_day)
                    except ValueError:
                         last_day = calendar.monthrange(prev_month_end.year, prev_month_end.month)[1]
                         last_statement_date = date(prev_month_end.year, prev_month_end.month, last_day)
                
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
                ls_midnight = datetime.combine(last_statement_date, time(23, 59, 59, 999999))
                ps_midnight = None
                if prev_statement_date:
                    ps_midnight = datetime.combine(prev_statement_date, time(23, 59, 59, 999999))
                
                # Queries
                unbilled_raw = db.query(func.sum(models.Transaction.amount)).filter(
                    models.Transaction.account_id == card.id, models.Transaction.date > ls_midnight,
                    models.Transaction.amount < 0, models.Transaction.exclude_from_reports == False
                ).scalar()
                unbilled_purchases_raw = Decimal(unbilled_raw or 0)

                payments_raw = db.query(func.sum(models.Transaction.amount)).filter(
                    models.Transaction.account_id == card.id, models.Transaction.date > ls_midnight,
                    models.Transaction.amount > 0, models.Transaction.exclude_from_reports == False
                ).scalar()
                current_cycle_payments_raw = Decimal(payments_raw or 0)
                
                if ps_midnight:
                    lc_raw = db.query(func.sum(models.Transaction.amount)).filter(
                        models.Transaction.account_id == card.id, models.Transaction.date > ps_midnight,
                        models.Transaction.date <= ls_midnight, models.Transaction.amount < 0, 
                        models.Transaction.exclude_from_reports == False
                    ).scalar()
                    last_cycle_spend_raw = Decimal(lc_raw or 0)
                
                statement_balance = intel["balance"] - unbilled_purchases_raw - current_cycle_payments_raw
                if statement_balance < 0:
                    minimum_due = abs(statement_balance) * Decimal("0.05")
                    
            intel["statement_balance"] = abs(statement_balance)
            intel["unbilled_spend"] = abs(unbilled_purchases_raw)
            intel["last_cycle_spend"] = abs(last_cycle_spend_raw)
            intel["current_cycle_payments"] = abs(current_cycle_payments_raw)
            intel["minimum_due"] = abs(minimum_due)
            intel["last_bill_date"] = last_statement_date.isoformat() if last_statement_date else None

            if intel["due_day"]:
                try:
                    today = timezone.utcnow().date()
                    due_date = date(today.year, today.month, int(intel["due_day"]))
                    if due_date < today:
                        if today.month == 12: due_date = date(today.year + 1, 1, int(intel["due_day"]))
                        else: due_date = date(today.year, today.month + 1, int(intel["due_day"]))
                    intel["days_until_due"] = (due_date - today).days
                    intel["next_due_date"] = due_date.isoformat()
                except: pass

            credit_intelligence.append(intel)
            
        return credit_intelligence
