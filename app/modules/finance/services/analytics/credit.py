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
    def get_credit_intelligence(db: Session, tenant_id: str, accounts: List[Any]) -> List[Dict[str, Any]]:
        # Filter credit cards, handling both dict and object types
        credit_cards = []
        for a in accounts:
            a_type = a.get('type') if isinstance(a, dict) else getattr(a, 'type', None)
            if a_type == 'CREDIT_CARD':
                credit_cards.append(a)
                
        credit_intelligence = []
        
        for card in credit_cards:
            is_dict = isinstance(card, dict)
            
            def get_val(obj, key, default=None):
                return obj.get(key, default) if is_dict else getattr(obj, key, default)

            card_id = get_val(card, 'id')
            card_name = get_val(card, 'name')
            card_limit = get_val(card, 'credit_limit')
            card_balance = get_val(card, 'balance')
            card_billing_day = get_val(card, 'billing_day')
            card_due_day = get_val(card, 'due_day')

            limit = Decimal(card_limit or 0)
            if limit == 0: limit = Decimal(100000.0) # Default limit fallback
                
            balance = Decimal(card_balance or 0)
            available_limit = max(Decimal(0), limit - balance)
            
            intel = {
                "id": str(card_id),
                "name": card_name,
                "balance": balance,
                "limit": limit,
                "available_limit": available_limit,
                "utilization": 0.0,
                "billing_day": int(card_billing_day) if card_billing_day else None,
                "due_day": int(card_due_day) if card_due_day else None,
                "status": "Healthy"
            }
            
            if limit > 0:
                intel["utilization"] = float((balance / limit) * 100)
                if intel["utilization"] > 80:
                    intel["status"] = "High Utilization"
                elif intel["utilization"] > 50:
                    intel["status"] = "Moderate"

            # Billing Cycle Logic
            last_statement_date = None
            due_date = None
            
            if intel["billing_day"]:
                billing_day = int(intel["billing_day"])
                today = timezone.utcnow().date()
                
                # Calculate the most recent statement date
                try:
                    this_month_stmt = date(today.year, today.month, billing_day)
                except ValueError:
                    # Handle end of month (e.g., billing day 31 in a 30-day month)
                    last_day = calendar.monthrange(today.year, today.month)[1]
                    this_month_stmt = date(today.year, today.month, last_day)

                if today >= this_month_stmt:
                    last_statement_date = this_month_stmt
                else:
                    # Move to previous month
                    month = today.month - 1
                    year = today.year
                    if month == 0:
                        month = 12
                        year -= 1
                    
                    try:
                        last_statement_date = date(year, month, billing_day)
                    except ValueError:
                        last_day = calendar.monthrange(year, month)[1]
                        last_statement_date = date(year, month, last_day)

                # Calculate Due Date
                if intel["due_day"]:
                    due_day = int(intel["due_day"])
                    due_year = last_statement_date.year
                    due_month = last_statement_date.month
                    
                    # If due_day <= billing_day, due is in the NEXT month
                    if due_day <= billing_day:
                        due_month += 1
                        if due_month > 12:
                            due_month = 1
                            due_year += 1
                        
                    try:
                        due_date = date(due_year, due_month, due_day)
                    except ValueError:
                        last_day = calendar.monthrange(due_year, due_month)[1]
                        due_date = date(due_year, due_month, last_day)
                    
                    if due_date < today:
                        adv_month = due_month + 1
                        adv_year = due_year
                        if adv_month > 12:
                            adv_month = 1
                            adv_year += 1
                        try:
                            due_date = date(adv_year, adv_month, due_day)
                        except ValueError:
                            last_day = calendar.monthrange(adv_year, adv_month)[1]
                            due_date = date(adv_year, adv_month, last_day)

            if last_statement_date:
                intel["last_statement_date"] = last_statement_date.isoformat()
                intel["last_bill_date"] = intel["last_statement_date"] # Alias for frontend
                ls_midnight = datetime.combine(last_statement_date, time(23, 59, 59, 999999))
                
                # Previous cycle date for historical context
                p_month = last_statement_date.month - 1
                p_year = last_statement_date.year
                if p_month == 0:
                    p_month = 12
                    p_year -= 1
                try:
                    prev_stmt_date = date(p_year, p_month, billing_day)
                except ValueError:
                    prev_stmt_date = date(p_year, p_month, calendar.monthrange(p_year, p_month)[1])
                
                ps_midnight = datetime.combine(prev_stmt_date, time(23, 59, 59, 999999))

                # Unbilled spend = Purchases AFTER last statement (excluding hidden)
                unbilled_raw = db.query(func.sum(models.Transaction.amount)).filter(
                    models.Transaction.account_id == str(card_id),
                    models.Transaction.date > ls_midnight,
                    models.Transaction.amount < 0,
                    models.Transaction.is_transfer == False,
                    models.Transaction.exclude_from_reports == False
                ).scalar()
                
                unbilled_spend = abs(Decimal(unbilled_raw or 0))
                
                # Payments made AFTER last statement
                payments_raw = db.query(func.sum(models.Transaction.amount)).filter(
                    models.Transaction.account_id == str(card_id),
                    models.Transaction.date > ls_midnight,
                    models.Transaction.amount > 0,
                    models.Transaction.is_transfer == False,
                    models.Transaction.exclude_from_reports == False
                ).scalar()
                current_cycle_payments = Decimal(payments_raw or 0)

                # Last cycle spend = Purchases BETWEEN prev statement and last statement
                last_cycle_raw = db.query(func.sum(models.Transaction.amount)).filter(
                    models.Transaction.account_id == str(card_id),
                    models.Transaction.date > ps_midnight,
                    models.Transaction.date <= ls_midnight,
                    models.Transaction.amount < 0,
                    models.Transaction.is_transfer == False,
                    models.Transaction.exclude_from_reports == False
                ).scalar()
                
                # Last cycle payments
                last_cycle_payments_raw = db.query(func.sum(models.Transaction.amount)).filter(
                    models.Transaction.account_id == str(card_id),
                    models.Transaction.date > ps_midnight,
                    models.Transaction.date <= ls_midnight,
                    models.Transaction.amount > 0,
                    models.Transaction.is_transfer == False,
                    models.Transaction.exclude_from_reports == False
                ).scalar()
                
                # Statement balance = Current Balance - Unbilled + Payments
                statement_balance = balance - unbilled_spend + current_cycle_payments
                
                intel["statement_balance"] = max(Decimal(0), statement_balance)
                intel["unbilled_spend"] = unbilled_spend
                intel["current_cycle_spend"] = unbilled_spend
                intel["current_cycle_payments"] = current_cycle_payments
                intel["last_cycle_spend"] = abs(Decimal(last_cycle_raw or 0))
                intel["last_cycle_payments"] = Decimal(last_cycle_payments_raw or 0)
                intel["minimum_due"] = intel["statement_balance"] * Decimal("0.05")
            
            if due_date:
                today = timezone.utcnow().date()
                intel["next_due_date"] = due_date.isoformat()
                intel["days_until_due"] = (due_date - today).days
                if intel["days_until_due"] < 0:
                    intel["status"] = "Overdue"
                elif intel["days_until_due"] <= 3:
                    intel["status"] = "Due Soon"

            # Final naming alignment for frontend
            intel["credit_limit"] = intel.pop("limit")
            credit_intelligence.append(intel)
            
        return credit_intelligence
