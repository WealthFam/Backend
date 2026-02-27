import logging
from backend.app.modules.auth.security import get_password_hash

logger = logging.getLogger(__name__)
from backend.app.core.database import SessionLocal
from backend.app.modules.auth.models import User, Tenant, UserRole
from backend.app.modules.finance.models import (
    Account, AccountType, Transaction, TransactionType, Category, 
    Loan, LoanType, MutualFundsMeta, MutualFundHolding, MutualFundOrder,
    Budget, ExpenseGroup
)
from datetime import timedelta
from backend.app.core import timezone
import random
import uuid

def seed_data():
    db = SessionLocal()
    try:
        demo_email = "demo@demo.com"
        user = db.query(User).filter(User.email == demo_email).first()
        
        if not user:
            logger.info(f"Creating demo user: {demo_email}")
            
            # 1. Create Tenant
            tenant = Tenant(name="Demo Family")
            db.add(tenant)
            db.commit()
            db.refresh(tenant)
            
            # 2. Create User
            user = User(
                email=demo_email,
                password_hash=get_password_hash("demo123"),
                full_name="Demo User",
                tenant_id=tenant.id,
                role=UserRole.OWNER
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            logger.info("Demo user already exists.")
            tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()

        tenant_id = tenant.id
        user_id = user.id

        # 3. Create Accounts
        accounts = db.query(Account).filter(Account.owner_id == user_id).all()
        if not accounts:
            logger.info("Seeding accounts...")
            
            # Bank
            acc_bank = Account(
                id=str(uuid.uuid4()), tenant_id=tenant_id, owner_id=user_id, name="HDFC Salary", type=AccountType.BANK, 
                balance=50000, last_synced_balance=50000, last_synced_at=timezone.utcnow()
            )
            # Credit Card
            acc_cc = Account(
                id=str(uuid.uuid4()), tenant_id=tenant_id, owner_id=user_id, name="Amazon Pay ICICI", type=AccountType.CREDIT_CARD, 
                credit_limit=200000, balance=15000, 
                last_synced_balance=15000, last_synced_limit=200000, last_synced_at=timezone.utcnow()
            )
            # Wallet
            acc_wallet = Account(
                id=str(uuid.uuid4()), tenant_id=tenant_id, owner_id=user_id, name="Cash & Wallet", type=AccountType.WALLET, 
                balance=2500, last_synced_balance=2500, last_synced_at=timezone.utcnow()
            )
            # Loan Account
            acc_loan = Account(
                id=str(uuid.uuid4()), tenant_id=tenant_id, owner_id=user_id, name="Home Loan", type=AccountType.LOAN, 
                balance=0, last_synced_balance=0, last_synced_at=timezone.utcnow()
            )
            
            db.add_all([acc_bank, acc_cc, acc_wallet, acc_loan])
            db.commit()

            # Create Snapshots
            from backend.app.modules.finance.models import BalanceSnapshot
            snapshots = []
            for acc in [acc_bank, acc_cc, acc_wallet, acc_loan]:
                snapshots.append(BalanceSnapshot(
                    account_id=acc.id,
                    tenant_id=tenant_id,
                    balance=acc.balance,
                    credit_limit=acc.credit_limit,
                    timestamp=acc.last_synced_at,
                    source="SEEDER"
                ))
            db.add_all(snapshots)
            db.commit()
            
            accounts_dict = {
                "BANK": acc_bank,
                "CREDIT_CARD": acc_cc,
                "WALLET": acc_wallet,
                "LOAN": acc_loan
            }
        else:
            accounts_dict = {
                "BANK": next((a for a in accounts if a.type == AccountType.BANK), None),
                "CREDIT_CARD": next((a for a in accounts if a.type == AccountType.CREDIT_CARD), None),
                "WALLET": next((a for a in accounts if a.type == AccountType.WALLET), None),
                "LOAN": next((a for a in accounts if a.type == AccountType.LOAN), None),
            }

        # 4. Loan Details
        if accounts_dict["LOAN"]:
            existing_loan = db.query(Loan).filter(Loan.account_id == accounts_dict["LOAN"].id).first()
            if not existing_loan:
                logger.info("Seeding Home Loan...")
                loan = Loan(
                    tenant_id=tenant_id,
                    account_id=accounts_dict["LOAN"].id,
                    principal_amount=5000000,
                    interest_rate=8.5,
                    start_date=timezone.utcnow() - timedelta(days=365*2), # 2 years ago
                    tenure_months=240, # 20 years
                    emi_amount=43391,
                    emi_date=5,
                    bank_account_id=accounts_dict["BANK"].id,
                    loan_type=LoanType.HOME_LOAN
                )
                db.add(loan)
                db.commit()

        # 5. Mutual Funds
        mf_scheme = "123456"
        existing_meta = db.query(MutualFundsMeta).filter(MutualFundsMeta.scheme_code == mf_scheme).first()
        if not existing_meta:
            logger.info("Seeding Mutual Funds...")
            meta = MutualFundsMeta(
                scheme_code=mf_scheme,
                scheme_name="Nifty 50 Index Fund",
                fund_house="HDFC Mutual Fund",
                category="Equity"
            )
            db.add(meta)
            db.commit() # Commit Meta first
            
            # Holding
            holding = MutualFundHolding(
                tenant_id=tenant_id,
                user_id=user_id,
                scheme_code=mf_scheme,
                units=100.50,
                average_price=150.00,
                current_value=18000.00,
                last_nav=179.10
            )
            db.add(holding)
            db.commit() # Commit Holding
            
            # Order History (SIP)
            for i in range(6):
                order_date = timezone.utcnow() - timedelta(days=30*i)
                order = MutualFundOrder(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    holding_id=holding.id,
                    scheme_code=mf_scheme,
                    type="BUY",
                    amount=5000,
                    units=33.33,
                    nav=150.0,
                    order_date=order_date,
                    status="COMPLETED"
                )
                db.add(order)
            db.commit()

        if not categories:
            logger.info("Seeding categories...")
            
            # 1. Root: Food
            food = Category(tenant_id=tenant_id, name="Food", type="expense", icon="🍔")
            db.add(food)
            db.commit()
            db.refresh(food)
            
            # 2. Children of Food
            db.add_all([
                Category(tenant_id=tenant_id, name="Groceries", type="expense", icon="🛒", parent_id=food.id),
                Category(tenant_id=tenant_id, name="Dining Out", type="expense", icon="🍕", parent_id=food.id),
            ])
            
            # 3. Others
            for name in ["Transport", "Shopping", "Salary", "Investments", "Transfers"]:
                ctype = "expense"
                if name == "Salary": ctype = "income"
                elif name == "Transfers": ctype = "transfer"
                db.add(Category(tenant_id=tenant_id, name=name, type=ctype))
            
            db.commit()
            categories = db.query(Category).filter(Category.tenant_id == tenant_id).all()
        
        def get_cat_id(name):
            for c in categories:
                if c.name == name: return c.id
            return categories[0].id

        # 7. Transactions (Regular & Linked)
        # Check if transactions exist for any of the user's accounts
        acc_ids = [a.id for a in accounts_dict.values() if a]
        if db.query(Transaction).filter(Transaction.account_id.in_(acc_ids)).count() == 0:
            logger.info("Seeding transactions...")
            
            # A. Linked Transfer (Credit Card Bill Payment)
            t1_id = str(uuid.uuid4())
            t2_id = str(uuid.uuid4())
            transfer_cat_id = get_cat_id("Transfers")
            
            # Debit from Bank
            txn1 = Transaction(
                id=t1_id,
                tenant_id=tenant_id,
                account_id=accounts_dict["BANK"].id,
                type=TransactionType.DEBIT,
                amount=15000,
                date=timezone.utcnow() - timedelta(days=2),
                description="Credit Card Bill Payment",
                category=transfer_cat_id,
                is_transfer=True,
                linked_transaction_id=t2_id
            )
            
            # Credit to CC
            txn2 = Transaction(
                id=t2_id,
                tenant_id=tenant_id,
                account_id=accounts_dict["CREDIT_CARD"].id,
                type=TransactionType.CREDIT,
                amount=15000,
                date=timezone.utcnow() - timedelta(days=2),
                description="Bill Payment Received",
                category=transfer_cat_id,
                is_transfer=True,
                linked_transaction_id=t1_id
            )
            
            db.add(txn1)
            db.add(txn2)
            
            # B. Salary
            db.add(Transaction(
                tenant_id=tenant_id, 
                account_id=accounts_dict["BANK"].id,
                type=TransactionType.CREDIT,
                amount=85000,
                date=timezone.utcnow().replace(day=1), # 1st of month
                description="Salary",
                category=get_cat_id("Salary")
            ))
            
            # C. Random Spend
            shopping_cat_id = get_cat_id("Shopping")
            for i in range(15):
                db.add(Transaction(
                    tenant_id=tenant_id,
                    account_id=accounts_dict["CREDIT_CARD"].id,
                    type=TransactionType.DEBIT,
                    amount=random.randint(100, 2000),
                    date=timezone.utcnow() - timedelta(days=random.randint(1, 20)),
                    description=f"Purchase at Shop {i}",
                    category=shopping_cat_id
                ))

            # D. Budgets
            existing_budgets = db.query(Budget).filter(Budget.tenant_id == tenant_id).all()
            if not existing_budgets:
                logger.info("Seeding budgets...")
                db.add(Budget(tenant_id=tenant_id, category="Food", amount_limit=15000))
                db.add(Budget(tenant_id=tenant_id, category="Transport", amount_limit=5000))
                db.add(Budget(tenant_id=tenant_id, category="Shopping", amount_limit=10000))
                db.commit()

            # E. Expense Groups
            existing_groups = db.query(ExpenseGroup).filter(ExpenseGroup.tenant_id == tenant_id).all()
            if not existing_groups:
                logger.info("Seeding expense groups...")
                group = ExpenseGroup(
                    tenant_id=tenant_id,
                    name="Thailand Trip 2024",
                    description="Personal vacation expenses",
                    budget=120000,
                    icon="🌴",
                    is_active=True
                )
                db.add(group)
                db.commit()
                db.refresh(group)
                
                # Link last 3 transactions to this group
                last_transactions = db.query(Transaction).filter(
                    Transaction.tenant_id == tenant_id,
                    Transaction.type == TransactionType.DEBIT
                ).order_by(Transaction.date.desc()).limit(3).all()
                
                for t in last_transactions:
                    t.expense_group_id = group.id
                db.commit()

            db.commit()
            logger.info("Seeding complete!")

    except Exception as e:
        logger.info(f"Error seeding data: {e}")
        logger.exception("Traceback:")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
