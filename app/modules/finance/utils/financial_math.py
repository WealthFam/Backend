from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Tuple

def xirr(cash_flows: List[Tuple[datetime, float]], guess: float = 0.1) -> float:
    """
    Calculate XIRR (Extended Internal Rate of Return) using Newton-Raphson method.
    
    Args:
        cash_flows: List of (date, amount) tuples. Negative = outflow, Positive = inflow
        guess: Initial guess for IRR (default 10%)
    
    Returns:
        Annualized return as decimal (e.g., 0.125 for 12.5%)
    """
    if not cash_flows or len(cash_flows) < 2:
        return 0.0
    
    # Sort by date
    cash_flows = sorted(cash_flows, key=lambda x: x[0])
    
    # Base date (first transaction)
    base_date = cash_flows[0][0]
    
    # Calculate days from base for each cash flow
    days = [(cf[0] - base_date).days for cf in cash_flows]
    amounts = [cf[1] for cf in cash_flows]
    
    # Newton-Raphson iteration
    rate = guess
    epsilon = 1e-6  # Precision
    max_iterations = 100
    
    for _ in range(max_iterations):
        # Calculate NPV and its derivative
        npv = sum(amt / ((1 + rate) ** (day / 365.0)) for day, amt in zip(days, amounts))
        dnpv = sum(-amt * day / 365.0 / ((1 + rate) ** (day / 365.0 + 1)) for day, amt in zip(days, amounts))
        
        if abs(npv) < epsilon:
            return rate
        
        if dnpv == 0:
            return 0.0
        
        # Newton-Raphson update
        rate = rate - npv / dnpv
        
        # Prevent extreme values
        if rate < -0.99:
            rate = -0.99
        elif rate > 10:
            rate = 10
    
    return rate


def categorize_fund(scheme_category: str) -> str:
    """
    Categorize fund based on AMFI scheme category.
    
    Returns: 'equity', 'debt', 'hybrid', or 'other'
    """
    if not scheme_category:
        return 'other'
    
    category_lower = scheme_category.lower()
    
    # Equity patterns
    equity_keywords = ['equity', 'index', 'large cap', 'mid cap', 'small cap', 
                       'multi cap', 'flexi cap', 'focused', 'sectoral', 'thematic',
                       'elss', 'value', 'contra', 'dividend yield']
    
    # Debt patterns
    debt_keywords = ['debt', 'liquid', 'gilt', 'bond', 'income', 'credit', 
                     'dynamic bond', 'banking', 'psu', 'corporate', 'overnight',
                     'ultra short', 'low duration', 'medium duration', 'long duration']
    
    # Hybrid patterns
    hybrid_keywords = ['hybrid', 'balanced', 'allocation', 'arbitrage', 
                       'equity savings', 'multi asset']
    
    for keyword in equity_keywords:
        if keyword in category_lower:
            return 'equity'
    
    for keyword in debt_keywords:
        if keyword in category_lower:
            return 'debt'
    
    for keyword in hybrid_keywords:
        if keyword in category_lower:
            return 'hybrid'
    
    return 'other'


def calculate_start_date(period: str, first_transaction_date) -> datetime:
    """
    Calculate start date based on period string.
    
    Args:
        period: One of '1m', '3m', '6m', '1y', 'all'
        first_transaction_date: Date of first transaction
    
    Returns:
        datetime object for start date
    """
    from datetime import date
    from dateutil.relativedelta import relativedelta
    
    from backend.app.core.timezone import utcnow
    
    today = utcnow().date()
    
    # Convert to date if datetime
    if hasattr(first_transaction_date, 'date'):
        first_date = first_transaction_date.date()
    else:
        first_date = first_transaction_date
    
    period_map = {
        '1m': relativedelta(months=1),
        '3m': relativedelta(months=3),
        '6m': relativedelta(months=6),
        '1y': relativedelta(years=1),
        'all': None
    }
    
    from datetime import timedelta
    if period == 'all' or period not in period_map:
        return first_date - timedelta(days=10)
    
    delta = period_map[period]
    calculated_start = today - delta
    
    # Don't go before first transaction - add 10 days buffer for visual context
    from datetime import timedelta
    return max(calculated_start, first_date - timedelta(days=10))


def add_months(source_date, months: int):
    """Add months to a date."""
    from dateutil.relativedelta import relativedelta
    return source_date + relativedelta(months=months)


def simulate_loan_repayment(
    principal: Decimal,
    annual_interest_rate: Decimal,
    emi_amount: Decimal,
    extra_monthly_payment: Decimal = Decimal("0"),
    one_time_prepayment: Decimal = Decimal("0")
) -> Dict[str, Any]:
    """
    Simulates a single loan repayment path and returns summary statistics.

    Converts Decimal inputs to float internally for iterative performance;
    monetary outputs are rounded to 2 decimal places.
    """
    balance = float(principal - one_time_prepayment)
    if balance < 0:
        balance = 0.0

    monthly_rate = float(annual_interest_rate) / 100 / 12
    effective_payment = float(emi_amount + extra_monthly_payment)
    total_interest = 0.0
    months = 0
    schedule = []

    # Safety cap: prevent infinite loops when payment cannot cover interest
    max_months = 600

    while balance > 0 and months < max_months:
        months += 1
        interest = balance * monthly_rate
        total_interest += interest
        principal_part = effective_payment - interest

        if principal_part <= 0:
            return {"total_interest": float("inf"), "months": max_months, "is_viable": False, "schedule": []}

        balance -= principal_part
        if balance < 0:
            balance = 0.0
        
        schedule.append({
            "month": months,
            "balance": round(balance, 2),
            "interest_payment": round(interest, 2),
            "principal_payment": round(principal_part, 2)
        })

    return {
        "total_interest": round(total_interest, 2),
        "months": months,
        "is_viable": True,
        "schedule": schedule
    }


def run_loan_scenarios(
    principal: Decimal,
    annual_interest_rate: Decimal,
    emi_amount: Decimal,
) -> Dict[str, Any]:
    """Runs three strategic prepayment scenarios against the standard baseline."""
    standard = simulate_loan_repayment(principal, annual_interest_rate, emi_amount)

    aggressive = simulate_loan_repayment(
        principal, annual_interest_rate, emi_amount,
        extra_monthly_payment=emi_amount * Decimal("0.1"),
    )
    bulk = simulate_loan_repayment(
        principal, annual_interest_rate, emi_amount,
        one_time_prepayment=principal * Decimal("0.1"),
    )
    anniversary = simulate_loan_repayment(
        principal, annual_interest_rate, emi_amount,
        extra_monthly_payment=emi_amount / Decimal("12"),
    )

    emi_float = float(emi_amount)
    principal_float = float(principal)

    return {
        "standard": standard,
        "scenarios": [
            {
                "name": "Aggressive (+10% EMI)",
                "description": f"Increasing your EMI by {round(emi_float * 0.1, 0):,.0f}",
                "interest_saved": round(
                    standard["total_interest"] - aggressive["total_interest"], 2
                ),
                "months_saved": standard["months"] - aggressive["months"],
                "total_interest": aggressive["total_interest"],
                "months": aggressive["months"],
            },
            {
                "name": "Strategic Bulk (10% Principal)",
                "description": f"One-time prepayment of {round(principal_float * 0.1, 0):,.0f}",
                "interest_saved": round(standard["total_interest"] - bulk["total_interest"], 2),
                "months_saved": standard["months"] - bulk["months"],
                "total_interest": bulk["total_interest"],
                "months": bulk["months"],
            },
            {
                "name": "Anniversary Boost (1 Extra EMI/Year)",
                "description": "Paying one extra EMI every year (distributed monthly)",
                "interest_saved": round(
                    standard["total_interest"] - anniversary["total_interest"], 2
                ),
                "months_saved": standard["months"] - anniversary["months"],
                "total_interest": anniversary["total_interest"],
                "months": anniversary["months"],
            },
        ],
    }
