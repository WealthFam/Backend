import uuid
from typing import Optional
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Boolean
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import relationship, backref
from backend.app.core.database import Base
from backend.app.core import timezone
from backend.app.core.timezone import UTCDateTime
import enum

class AccountType(str, enum.Enum):
    BANK = "BANK"
    CREDIT_CARD = "CREDIT_CARD"
    LOAN = "LOAN"
    WALLET = "WALLET"
    INVESTMENT = "INVESTMENT"

class BalanceSnapshot(Base):
    __tablename__ = "balance_snapshots"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    account_id = Column(String, ForeignKey("accounts.id"), nullable=False, index=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    balance = Column(Numeric(15, 2), nullable=False)
    timestamp = Column(UTCDateTime, default=timezone.utcnow, nullable=False)
    source = Column(String, default="MANUAL") # SMS, EMAIL, MANUAL, CSV
    
    account = relationship("Account", backref=backref("snapshots", cascade="all, delete-orphan"))

class Account(Base):
    __tablename__ = "accounts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    owner_id = Column(String, ForeignKey("users.id"), nullable=True, index=True) # None = Shared Family Account
    name = Column(String, nullable=False)
    type = Column(SqlEnum(AccountType), nullable=False)
    currency = Column(String, default="INR", nullable=False)
    account_mask = Column(String, nullable=True) # e.g. "XX1234" used for SMS matching
    balance = Column(Numeric(15, 2), default=0.0) # Current Running Balance
    credit_limit = Column(Numeric(15, 2), nullable=True) # Current Credit Limit
    
    # Sync Anchors (Bank Reported)
    last_synced_balance = Column(Numeric(15, 2), nullable=True)
    last_synced_at = Column(UTCDateTime, nullable=True)
    last_synced_limit = Column(Numeric(15, 2), nullable=True)

    billing_day = Column(Numeric(2, 0), nullable=True) # 1-31
    due_day = Column(Numeric(2, 0), nullable=True) # 1-31
    is_verified = Column(Boolean, default=True, nullable=False) # False = Auto-detected from SMS
    import_config = Column(String, nullable=True) # JSON config for CSV/Excel mapping
    created_at = Column(UTCDateTime, default=timezone.utcnow)

    transactions = relationship("Transaction", back_populates="account", cascade="all, delete-orphan",
                               primaryjoin="Account.id == Transaction.account_id",
                               foreign_keys="Transaction.account_id",
                               viewonly=True,
                               sync_backref=False)
                               
    loan_details = relationship("Loan", uselist=False, back_populates="account")
    owner = relationship("User", foreign_keys=[owner_id])


class TransactionType(str, enum.Enum):
    CREDIT = "CREDIT"
    DEBIT = "DEBIT"

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    account_id = Column(String, nullable=False, index=True)  # No FK to avoid DuckDB constraint
    type = Column(SqlEnum(TransactionType), default=TransactionType.DEBIT, nullable=False)
    amount = Column(Numeric(15, 2), nullable=False) # Precision for currency
    date = Column(UTCDateTime, nullable=False, index=True)
    description = Column(String, nullable=True)
    recipient = Column(String, nullable=True) # Extracted merchant/payee name
    category = Column(String, nullable=True) # Keeping simple string for now, could be FK later
    tags = Column(String, nullable=True) # JSON Array string
    content_hash = Column(String, nullable=True, index=True)
    external_id = Column(String, nullable=True) # For de-duplication
    is_transfer = Column(Boolean, default=False, nullable=False)
    linked_transaction_id = Column(String, nullable=True) # ID of the other leg of a transfer
    source = Column(String, default="MANUAL", nullable=False) # MANUAL, CSV, EXCEL, etc.
    latitude = Column(Numeric(10, 8), nullable=True)
    longitude = Column(Numeric(11, 8), nullable=True)
    location_name = Column(String, nullable=True)
    expense_group_id = Column(String, ForeignKey("expense_groups.id"), nullable=True)
    exclude_from_reports = Column(Boolean, default=False, nullable=False)
    is_emi = Column(Boolean, default=False, nullable=False)
    loan_id = Column(String, ForeignKey("loans.id"), nullable=True)
    created_at = Column(UTCDateTime, default=timezone.utcnow)

    expense_group = relationship("ExpenseGroup", back_populates="transactions")

    linked_transaction = relationship("Transaction", 
        remote_side=[id],
        primaryjoin="Transaction.linked_transaction_id==Transaction.id",
        foreign_keys=[linked_transaction_id],
        uselist=False,
        post_update=True
    )

    @property
    def transfer_account_id(self):
        if self.linked_transaction:
            return self.linked_transaction.account_id
        return None

    account = relationship("Account", back_populates="transactions",
                          primaryjoin="Transaction.account_id == Account.id",
                          foreign_keys="Transaction.account_id",
                          viewonly=True,
                          sync_backref=False)
    
    loan = relationship("Loan", backref="emi_transactions")


class CategoryRule(Base):
    __tablename__ = "category_rules"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String, nullable=False) # e.g. "Food Apps"
    category = Column(String, nullable=False) # Target Category e.g. "Food"
    keywords = Column(String, nullable=False) # JSON List of strings e.g. '["Zomato", "Swiggy"]'
    priority = Column(Numeric(5,0), default=0) # Higher priority runs first
    is_transfer = Column(Boolean, default=False, nullable=False)
    to_account_id = Column(String, nullable=True) # Destination Account ID if it's a transfer rule
    exclude_from_reports = Column(Boolean, default=False, nullable=False)
    created_at = Column(UTCDateTime, default=timezone.utcnow)

class IgnoredSuggestion(Base):
    __tablename__ = "ignored_suggestions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    pattern = Column(String, nullable=False) # The description/keyword to ignore
    created_at = Column(UTCDateTime, default=timezone.utcnow)

class Category(Base):
    __tablename__ = "categories"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    icon = Column(String, nullable=True) # Emoji or icon code
    color = Column(String, default="#3B82F6") # Hex color code
    type = Column(String, default="expense") # expense/income
    parent_id = Column(String, ForeignKey("categories.id"), nullable=True)
    created_at = Column(UTCDateTime, default=timezone.utcnow)

    subcategories = relationship("Category", backref=backref("parent", remote_side=[id]))

    @property
    def parent_name(self) -> Optional[str]:
        return self.parent.name if self.parent else None

class Budget(Base):
    __tablename__ = "budgets"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    category = Column(String, nullable=False, index=True) # e.g. "Food"
    amount_limit = Column(Numeric(15, 2), nullable=False) # Monthly Limit
    period = Column(String, default="MONTHLY") # For future extensibility
    updated_at = Column(UTCDateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ExpenseGroup(Base):
    __tablename__ = "expense_groups"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(UTCDateTime, default=timezone.utcnow)
    start_date = Column(UTCDateTime, nullable=True)
    end_date = Column(UTCDateTime, nullable=True)
    budget = Column(Numeric(15, 2), default=0.0)
    icon = Column(String, nullable=True)

    transactions = relationship("Transaction", back_populates="expense_group")


class Frequency(str, enum.Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"

class LoanType(str, enum.Enum):
    HOME_LOAN = "HOME_LOAN"
    PERSONAL_LOAN = "PERSONAL_LOAN"
    CAR_LOAN = "CAR_LOAN"
    EDUCATION_LOAN = "EDUCATION_LOAN"
    CREDIT_CARD = "CREDIT_CARD"
    OTHER = "OTHER"

class RecurringTransaction(Base):
    __tablename__ = "recurring_transactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String, nullable=False) # e.g. "Netflix Subscription"
    amount = Column(Numeric(15, 2), nullable=False)
    type = Column(SqlEnum(TransactionType), default=TransactionType.DEBIT, nullable=False)
    category = Column(String, nullable=True)
    account_id = Column(String, nullable=False, index=True)
    
    frequency = Column(SqlEnum(Frequency), default=Frequency.MONTHLY, nullable=False)
    start_date = Column(UTCDateTime, nullable=False)
    next_run_date = Column(UTCDateTime, nullable=False, index=True)
    
    is_active = Column(Boolean, default=True, nullable=False)
    exclude_from_reports = Column(Boolean, default=False, nullable=False)
    last_run_date = Column(UTCDateTime, nullable=True) # To track when it last ran
    created_at = Column(UTCDateTime, default=timezone.utcnow)

class Loan(Base):
    __tablename__ = "loans"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    account_id = Column(String, ForeignKey("accounts.id"), nullable=False, unique=True, index=True) # One-to-one with Loan Account
    
    principal_amount = Column(Numeric(15, 2), nullable=False)
    interest_rate = Column(Numeric(5, 2), nullable=False) # Annual Interest Rate %
    start_date = Column(UTCDateTime, nullable=False)
    tenure_months = Column(Numeric(5,0), nullable=False)
    
    emi_amount = Column(Numeric(15, 2), nullable=False)
    emi_date = Column(Numeric(2, 0), nullable=False) # Day of month (1-31)
    
    bank_account_id = Column(String, nullable=True) # Source account for EMI deduction
    loan_type = Column(SqlEnum(LoanType), default=LoanType.OTHER, nullable=False)
    
    created_at = Column(UTCDateTime, default=timezone.utcnow)

    account = relationship("Account", back_populates="loan_details")

class MutualFundsMeta(Base):
    __tablename__ = "mutual_funds_meta"

    scheme_code = Column(String, primary_key=True)
    scheme_name = Column(String, nullable=False)
    isin_growth = Column(String, nullable=True)
    isin_reinvest = Column(String, nullable=True)
    fund_house = Column(String, nullable=True)
    category = Column(String, nullable=True)
    updated_at = Column(UTCDateTime, default=datetime.utcnow)

class SelectionType(enum.Enum):
    MANUAL = "MANUAL"
    AUTO = "AUTO"

class InvestmentGoal(Base):
    __tablename__ = "investment_goals"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    target_amount = Column(Numeric(15, 2), nullable=False)
    target_date = Column(UTCDateTime, nullable=True)
    icon = Column(String, default="🎯")
    color = Column(String, default="#3b82f6")
    is_completed = Column(Boolean, default=False)
    owner_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(UTCDateTime, default=timezone.utcnow)

    holdings = relationship("MutualFundHolding", back_populates="goal")
    assets = relationship("GoalAsset", back_populates="goal", cascade="all, delete-orphan")

class GoalAssetType(str, enum.Enum):
    MUTUAL_FUND = "MUTUAL_FUND"
    BANK_ACCOUNT = "BANK_ACCOUNT" 
    MANUAL = "MANUAL"

class GoalAsset(Base):
    __tablename__ = "goal_assets"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    goal_id = Column(String, ForeignKey("investment_goals.id"), nullable=False, index=True)
    type = Column(SqlEnum(GoalAssetType), nullable=False)
    
    # Manual Entry Fields
    name = Column(String, nullable=True) # e.g. "EPF" or "My Savings"
    manual_amount = Column(Numeric(15, 2), nullable=True)
    interest_rate = Column(Numeric(5, 2), nullable=True) # %
    
    # Linked Entity Fields
    linked_account_id = Column(String, ForeignKey("accounts.id"), nullable=True)
    # For mutual funds, we might still use the separate holding relationship or link here. 
    # To keep it simple, we can migrate MF linking here eventually, but for now allow both or use this for "Portfolio" link.
    
    created_at = Column(UTCDateTime, default=timezone.utcnow)

    goal = relationship("InvestmentGoal", back_populates="assets")
    linked_account = relationship("Account")

    @property
    def current_value(self):
        if self.type == GoalAssetType.BANK_ACCOUNT and self.linked_account:
            return self.linked_account.balance
        return self.manual_amount or 0

    @property
    def display_name(self):
        # Convert type to string for safe comparison
        type_str = str(self.type.value if hasattr(self.type, 'value') else self.type).upper()
        if type_str == "BANK_ACCOUNT":
            if self.linked_account:
                return self.linked_account.name
            return self.name or "Linked Bank Account"
        return self.name or "Unnamed Asset"

class MutualFundHolding(Base):
    __tablename__ = "mutual_fund_holdings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    scheme_code = Column(String, ForeignKey("mutual_funds_meta.scheme_code"), nullable=False, index=True)
    folio_number = Column(String, nullable=True)
    units = Column(Numeric(15, 4), default=0)
    average_price = Column(Numeric(15, 4), default=0)
    current_value = Column(Numeric(15, 2), nullable=True)
    last_nav = Column(Numeric(15, 4), nullable=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    goal_id = Column(String, ForeignKey("investment_goals.id"), nullable=True)
    last_updated_at = Column(UTCDateTime, default=datetime.utcnow)

    goal = relationship("InvestmentGoal", back_populates="holdings")
    meta = relationship("MutualFundsMeta", foreign_keys=[scheme_code], primaryjoin="MutualFundHolding.scheme_code == MutualFundsMeta.scheme_code")

    @property
    def scheme_name(self):
        if self.meta and self.meta.scheme_name:
            return self.meta.scheme_name
        if self.folio_number:
            return f"Fund (Folio: {self.folio_number})"
        return f"Fund ({self.scheme_code})"

class MutualFundOrder(Base):
    __tablename__ = "mutual_fund_orders"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    holding_id = Column(String, nullable=True, index=True)
    scheme_code = Column(String, ForeignKey("mutual_funds_meta.scheme_code"), nullable=False, index=True)
    type = Column(String, default="BUY", nullable=False) # BUY, SELL
    amount = Column(Numeric(15, 2), nullable=False)
    units = Column(Numeric(15, 4), nullable=False)
    nav = Column(Numeric(15, 4), nullable=False)
    order_date = Column(UTCDateTime, nullable=False, index=True)
    folio_number = Column(String, nullable=True, index=True)
    status = Column(String, default="COMPLETED")
    external_id = Column(String, nullable=True)
    import_source = Column(String, default="MANUAL")
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(UTCDateTime, default=timezone.utcnow)

class PortfolioTimelineCache(Base):
    """Cache for portfolio timeline snapshots to avoid recalculating historical data"""
    __tablename__ = "portfolio_timeline_cache"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    snapshot_date = Column(UTCDateTime, nullable=False, index=True)  # Date of this snapshot
    portfolio_hash = Column(String, nullable=False, index=True)  # Hash of scheme_codes to detect changes
    portfolio_value = Column(Numeric(15, 2), nullable=False)
    invested_value = Column(Numeric(15, 2), nullable=False)
    benchmark_value = Column(Numeric(15, 2), nullable=True)
    created_at = Column(UTCDateTime, default=timezone.utcnow)
    
    # Composite index for fast lookups
    __table_args__ = (
        {'sqlite_autoincrement': True}
    )

class MutualFundSyncLog(Base):
    """Log to track background NAV sync status"""
    __tablename__ = "mutual_fund_sync_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    started_at = Column(UTCDateTime, default=datetime.utcnow)
    completed_at = Column(UTCDateTime, nullable=True)
    status = Column(String, default="running") # running, completed, error
    num_funds_updated = Column(Numeric(10, 0), default=0)
    error_message = Column(String, nullable=True)


