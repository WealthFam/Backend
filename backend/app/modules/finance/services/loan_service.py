from sqlalchemy.orm import Session
from backend.app.modules.finance.models import Account, AccountType, Loan, Transaction, TransactionType
from backend.app.modules.finance import models, schemas
from backend.app.core import timezone
import uuid
from dateutil.relativedelta import relativedelta

class LoanService:
    def create_loan(self, db: Session, loan_data: schemas.LoanCreate, tenant_id: str, owner_id: str = None) -> schemas.LoanRead:
        # 1. Create the Account (Liability)
        new_account = Account(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            owner_id=owner_id,
            name=loan_data.name,
            type=AccountType.LOAN,
            currency="INR",
            balance=loan_data.principal_amount, # Outstanding balance starts at Principal
            credit_limit=loan_data.principal_amount, # Max loan amount
            billing_day=loan_data.emi_date,
            is_verified=True,
            # Anchor Logic
            last_synced_balance=loan_data.principal_amount,
            last_synced_limit=loan_data.principal_amount,
            last_synced_at=loan_data.start_date or timezone.utcnow()
        )
        db.add(new_account)
        db.flush() # Generate ID
        
        # Initial Snapshot
        db.add(models.BalanceSnapshot(
            account_id=new_account.id,
            tenant_id=tenant_id,
            balance=loan_data.principal_amount,
            credit_limit=loan_data.principal_amount,
            timestamp=new_account.last_synced_at,
            source="LOAN_CREATION"
        ))
        
        # 2. Create the Loan details
        new_loan = Loan(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            account_id=new_account.id,
            principal_amount=loan_data.principal_amount,
            interest_rate=loan_data.interest_rate,
            start_date=loan_data.start_date,
            tenure_months=loan_data.tenure_months,
            emi_amount=loan_data.emi_amount,
            emi_date=loan_data.emi_date,
            loan_type=loan_data.loan_type,
            bank_account_id=str(loan_data.bank_account_id) if loan_data.bank_account_id else None
        )
        db.add(new_loan)
        db.commit()
        db.refresh(new_loan)
        
        return self._map_to_read_schema(new_loan, new_account)

    def record_repayment(self, db: Session, loan_id: str, repayment: schemas.LoanRepayment, tenant_id: str) -> schemas.LoanRead:
        from backend.app.modules.finance.services.transaction_service import TransactionService
        
        loan = db.query(Loan).filter(Loan.id == loan_id, Loan.tenant_id == tenant_id).first()
        if not loan:
            raise ValueError("Loan not found")
            
        # 1. Create Source Transaction (Debit from Bank)
        source_data = schemas.TransactionCreate(
            account_id=repayment.bank_account_id,
            amount=-repayment.amount,
            date=repayment.date,
            description=repayment.description or f"EMI Payment for {loan.account.name}",
            recipient=loan.account.name,
            category="Loan Repayment",
            is_emi=True,
            loan_id=loan.id,
            source="LOAN_SERVICE"
        )
        source_txn = TransactionService.create_transaction(db, source_data, tenant_id)
        
        # 2. Create Target Transaction (Credit to Loan)
        target_data = schemas.TransactionCreate(
            account_id=loan.account_id,
            amount=repayment.amount,
            date=repayment.date,
            description=repayment.description or f"Repayment Received",
            category="Transfer",
            is_transfer=True,
            is_emi=True,
            loan_id=loan.id,
            linked_transaction_id=str(source_txn.id),
            source="LOAN_SERVICE"
        )
        target_txn = TransactionService.create_transaction(db, target_data, tenant_id)
        
        # Link source back to target (TransactionService doesn't do this automatically for existing txns)
        source_txn.linked_transaction_id = str(target_txn.id)
        db.add(source_txn)
        db.commit()
        
        account = db.query(Account).filter(Account.id == loan.account_id).first()
        return self._map_to_read_schema(loan, account)

    def get_loans(self, db: Session, tenant_id: str, user_id: str = None) -> list[schemas.LoanRead]:
        query = db.query(Loan).filter(Loan.tenant_id == tenant_id)
        
        if user_id:
            # Filter by account ownership (user's loans or shared loans)
            from sqlalchemy import or_
            query = query.join(Account, Loan.account_id == Account.id)\
                         .filter(or_(Account.owner_id == user_id, Account.owner_id == None))
            
        loans = query.all()
        results = []
        for loan in loans:
            # Fetch associated account to get current balance
            account = db.query(Account).filter(Account.id == loan.account_id).first()
            if account:
                results.append(self._map_to_read_schema(loan, account))
        return results

    def get_loan_details(self, db: Session, loan_id: str, tenant_id: str) -> schemas.LoanDetail:
        loan = db.query(Loan).filter(Loan.id == loan_id, Loan.tenant_id == tenant_id).first()
        if not loan:
            return None
        
        account = db.query(Account).filter(Account.id == loan.account_id).first()
        base_read = self._map_to_read_schema(loan, account)
        
        # Generate Amortization Schedule
        schedule = self._generate_amortization_schedule(db, loan)
        
        return schemas.LoanDetail(
            **base_read.dict(),
            amortization_schedule=schedule
        )

    def _map_to_read_schema(self, loan: Loan, account: Account) -> schemas.LoanRead:
        outstanding = account.balance
        principal = loan.principal_amount
        paid = principal - outstanding
        progress = (paid / principal * 100) if principal > 0 else 0
        
        # Calculate next EMI date
        today = timezone.utcnow()
        # Simple logic: finds next occurrence of emi_date
        next_date = today.replace(day=int(loan.emi_date))
        if next_date < today:
            next_date = next_date + relativedelta(months=1)
            
        return schemas.LoanRead(
            id=loan.id,
            tenant_id=loan.tenant_id,
            account_id=loan.account_id,
            name=account.name,
            principal_amount=loan.principal_amount,
            interest_rate=loan.interest_rate,
            start_date=loan.start_date,
            tenure_months=loan.tenure_months,
            emi_amount=loan.emi_amount,
            emi_date=loan.emi_date,
            loan_type=loan.loan_type,
            bank_account_id=loan.bank_account_id,
            outstanding_balance=outstanding,
            paid_principal=paid,
            progress_percentage=round(float(progress), 2),
            next_emi_date=next_date,
            created_at=loan.created_at
        )

    def _generate_amortization_schedule(self, db: Session, loan: Loan) -> list[schemas.AmortizationScheduleItem]:
        # Fetch actual transactions to determine exact status
        paid_emi_txns = db.query(Transaction).filter(
            Transaction.loan_id == loan.id,
            Transaction.is_emi == True,
            Transaction.type == TransactionType.CREDIT # Repayment entering the loan account
        ).all()

        paid_months = set((t.date.year, t.date.month) for t in paid_emi_txns)

        schedule = []
        balance = loan.principal_amount
        r = (loan.interest_rate / 12) / 100 # Monthly interest rate
        
        current_date = loan.start_date
        
        for i in range(1, int(loan.tenure_months) + 1):
            interest = balance * r
            principal_part = loan.emi_amount - interest
            
            # Handling last installment rounding
            if balance < loan.emi_amount and i == int(loan.tenure_months):
                principal_part = balance
                emi = principal_part + interest
            else:
                emi = loan.emi_amount
            
            closing_balance = balance - principal_part
            if closing_balance < 0: closing_balance = 0
            
            # Determine status
            status = "PENDING"
            if (current_date.year, current_date.month) in paid_months:
                status = "PAID"
            elif current_date < timezone.utcnow():
                status = "OVERDUE"
            
            schedule.append(schemas.AmortizationScheduleItem(
                installment_no=i,
                due_date=current_date,
                opening_balance=round(balance, 2),
                emi=round(emi, 2),
                principal_component=round(principal_part, 2),
                interest_component=round(interest, 2),
                closing_balance=round(closing_balance, 2),
                status=status
            ))
            
            balance = closing_balance
            current_date = current_date + relativedelta(months=1)
            
            if balance <= 0:
                break
                
        return schedule
