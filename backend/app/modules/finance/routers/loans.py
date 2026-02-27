from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.modules.auth import models as auth_models
from backend.app.modules.auth.dependencies import get_current_user
from backend.app.modules.finance import schemas
from backend.app.modules.finance.services.loan_service import LoanService
from backend.app.modules.ingestion.ai_service import AIService

router = APIRouter()
service = LoanService()

@router.post("/loans", response_model=schemas.LoanRead)
def create_loan(
    loan: schemas.LoanCreate,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new Loan.
    """
    return service.create_loan(db, loan, str(current_user.tenant_id))

@router.post("/loans/{loan_id}/repayment", response_model=schemas.LoanRead)
def record_repayment(
    loan_id: str,
    repayment: schemas.LoanRepayment,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Record a loan repayment (EMI).
    """
    try:
        return service.record_repayment(db, loan_id, repayment, str(current_user.tenant_id))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/loans", response_model=List[schemas.LoanRead])
def get_loans(
    user_id: str | None = None,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all active loans.
    """
    return service.get_loans(db, str(current_user.tenant_id), user_id)

@router.get("/loans/{loan_id}", response_model=schemas.LoanDetail)
def get_loan_details(
    loan_id: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed loan information including the Amortization Schedule.
    """
    details = service.get_loan_details(db, loan_id, str(current_user.tenant_id))
    if not details:
        raise HTTPException(status_code=404, detail="Loan not found")
    return details

@router.post("/loans/portfolio/insights")
def generate_portfolio_insights(
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate AI insights for all active loans (Portfolio Analysis).
    """
    loans = service.get_loans(db, str(current_user.tenant_id))
    if not loans:
        return {"insights": "You have no active loans to analyze."}
    
    # Prepare data for AI
    loans_data = []
    for l in loans:
        loans_data.append({
            "name": l.name,
            "type": l.loan_type,
            "principal": float(l.principal_amount),
            "interest_rate": float(l.interest_rate),
            "tenure_months": l.tenure_months,
            "emi": float(l.emi_amount),
            "outstanding": float(l.outstanding_balance),
            "start_date": l.start_date.isoformat()
        })
    
    insight_text = AIService.generate_loans_overview_insights(db, str(current_user.tenant_id), loans_data)
    return {"insights": insight_text}

@router.post("/loans/{loan_id}/insights")
def generate_loan_insights(
    loan_id: str,
    current_user: auth_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate AI insights for a specific loan.
    """
    details = service.get_loan_details(db, loan_id, str(current_user.tenant_id))
    if not details:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    # Prepare data for AI
    loan_data = {
        "name": details.name,
        "type": details.loan_type,
        "principal": float(details.principal_amount),
        "interest_rate": float(details.interest_rate),
        "tenure_months": details.tenure_months,
        "emi": float(details.emi_amount),
        "outstanding": float(details.outstanding_balance),
        "start_date": details.start_date.isoformat(),
        "total_interest_payable": sum(float(x.interest_component) for x in details.amortization_schedule)
    }
    
    insight_text = AIService.generate_loan_insights(db, str(current_user.tenant_id), loan_data)
    return {"insights": insight_text}

