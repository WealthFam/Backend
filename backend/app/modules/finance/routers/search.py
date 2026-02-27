from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from backend.app.core.database import get_db
from backend.app.modules.auth import models as auth_models
from backend.app.modules.auth.dependencies import get_current_user
from sqlalchemy import func
from backend.app.modules.finance.models import Account, Loan, InvestmentGoal, MutualFundHolding, Transaction, MutualFundsMeta

router = APIRouter(prefix="/search", tags=["Search"])

class SearchResult(BaseModel):
    title: str
    subtitle: str
    value: Optional[str] = None
    type: str  # 'account', 'loan', 'goal', 'fund'
    color: Optional[str] = None
    id: Optional[str] = None
    code: Optional[str] = None
    route_params: Optional[dict] = None

@router.get("", response_model=List[SearchResult])
def global_search(
    q: str = Query(..., min_length=1),
    user_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: auth_models.User = Depends(get_current_user)
):
    tenant_id = str(current_user.tenant_id)
    query_low = q.lower()
    results = []

    # 1. Accounts
    accounts = db.query(Account).filter(
        Account.tenant_id == tenant_id,
        Account.name.ilike(f"%{q}%")
    ).all()
    for acc in accounts:
        results.append(SearchResult(
            title=acc.name,
            subtitle=f"{acc.type} • {acc.currency}",
            value=str(acc.balance),
            type='account',
            id=str(acc.id),
            color='info'
        ))

    # 2. Loans
    loans = db.query(Loan).join(Account).filter(
        Loan.tenant_id == tenant_id,
        Account.name.ilike(f"%{q}%")
    ).all()
    for loan in loans:
        results.append(SearchResult(
            title=loan.account.name,
            subtitle=f"{loan.loan_type} • {loan.interest_rate}%",
            value=str(loan.outstanding_balance),
            type='loan',
            id=str(loan.id),
            color='error'
        ))

    # 3. Investment Goals
    goals = db.query(InvestmentGoal).filter(
        InvestmentGoal.tenant_id == tenant_id,
        InvestmentGoal.name.ilike(f"%{q}%")
    ).all()
    for goal in goals:
        results.append(SearchResult(
            title=goal.name,
            subtitle=f"Progress: {goal.progress_percentage}%",
            value=str(goal.target_amount),
            type='goal',
            id=str(goal.id),
            color='success'
        ))

    # 4. Mutual Funds (Holdings joined with meta to search by name)
    holdings = db.query(MutualFundHolding).join(MutualFundsMeta).filter(
        MutualFundHolding.tenant_id == tenant_id,
        MutualFundsMeta.scheme_name.ilike(f"%{q}%")
    ).all()
    
    mf_groups = {}
    for h in holdings:
        code = h.scheme_code
        if code not in mf_groups:
            mf_groups[code] = {
                "title": h.scheme_name,
                "subtitle": (h.meta.category if h.meta else None) or "Mutual Fund",
                "current_value": 0,
                "code": code
            }
        mf_groups[code]["current_value"] += float(h.current_value or 0)

    for code, group in mf_groups.items():
        results.append(SearchResult(
            title=group["title"],
            subtitle=group["subtitle"],
            value=str(group["current_value"]),
            type='fund',
            code=code,
            color='primary'
        ))

    # 5. Merchants (Grouped by recipient from transactions)
    # This identifies merchants by their recipient name
    merchant_stats = db.query(
        Transaction.recipient,
        func.sum(Transaction.amount).label('total_spent'),
        func.count(Transaction.id).label('tx_count')
    ).filter(
        Transaction.tenant_id == tenant_id,
        Transaction.recipient.ilike(f"%{q}%"),
        Transaction.recipient != None,
        Transaction.recipient != ""
    ).group_by(Transaction.recipient).limit(10).all()

    for v_name, total, count in merchant_stats:
        results.append(SearchResult(
            title=v_name,
            subtitle=f"{count} Transactions • Merchant",
            value=str(total),
            type='merchant',
            id=v_name, # Use name as ID for routing
            color='warning' # Use warning/orange for merchants
        ))

    return results
