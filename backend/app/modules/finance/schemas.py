from pydantic import BaseModel
from typing import Optional, List, Union
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from backend.app.modules.finance.models import AccountType, TransactionType

class AccountBase(BaseModel):
    name: str
    type: AccountType
    currency: str = "INR"
    account_mask: Optional[str] = None
    balance: Optional[Decimal] = Decimal('0.0')
    credit_limit: Optional[Decimal] = None
    billing_day: Optional[int] = None
    due_day: Optional[int] = None
    is_verified: bool = True
    import_config: Optional[str] = None

class AccountCreate(AccountBase):
    owner_id: Optional[UUID] = None

    tenant_id: Optional[Union[UUID, str]] = None # Allow specifying a tenant

class AccountUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[AccountType] = None
    currency: Optional[str] = None
    account_mask: Optional[str] = None

    owner_id: Optional[UUID] = None
    balance: Optional[Decimal] = None
    credit_limit: Optional[Decimal] = None
    billing_day: Optional[int] = None
    due_day: Optional[int] = None
    is_verified: Optional[bool] = None
    import_config: Optional[str] = None
    tenant_id: Optional[Union[UUID, str]] = None


class AccountRead(AccountBase):
    id: Union[UUID, str]
    tenant_id: Union[UUID, str]
    owner_id: Optional[Union[UUID, str]] = None
    linked_goals: List[str] = []

    created_at: datetime

    class Config:
        from_attributes = True

class TransactionBase(BaseModel):
    amount: Decimal
    date: datetime
    description: Optional[str] = None
    recipient: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    is_transfer: bool = False
    linked_transaction_id: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    location_name: Optional[str] = None
    exclude_from_reports: bool = False
    is_emi: bool = False
    loan_id: Optional[str] = None
    expense_group_id: Optional[str] = None

class TransactionCreate(TransactionBase):
    account_id: UUID
    external_id: Optional[str] = None
    source: Optional[str] = "MANUAL"
    is_transfer: bool = False
    to_account_id: Optional[str] = None
    content_hash: Optional[str] = None

class TransactionUpdate(BaseModel):
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    date: Optional[datetime] = None
    amount: Optional[Decimal] = None
    is_transfer: Optional[bool] = None
    to_account_id: Optional[str] = None
    linked_transaction_id: Optional[str] = None
    exclude_from_reports: Optional[bool] = None
    is_emi: Optional[bool] = None
    loan_id: Optional[str] = None
    expense_group_id: Optional[str] = None

class Transaction(TransactionBase):
    id: Union[UUID, str]
    tenant_id: Union[UUID, str]
    account_id: Union[UUID, str]
    type: TransactionType
    created_at: datetime

    class Config:
        from_attributes = True

class TransactionRead(TransactionBase):
    id: Union[UUID, str]
    account_id: Union[UUID, str]
    tenant_id: Union[UUID, str]
    type: Optional[str] = "DEBIT"
    source: Optional[str] = "MANUAL"
    external_id: Optional[str] = None
    content_hash: Optional[str] = None
    transfer_account_id: Optional[UUID] = None
    exclude_from_reports: bool = False
    is_emi: bool = False
    loan_id: Optional[str] = None
    expense_group_id: Optional[str] = None

    class Config:
        from_attributes = True

class TransactionPagination(BaseModel):
    items: List[TransactionRead]
    total: int
    page: int
    size: int

class BulkDeleteRequest(BaseModel):
    transaction_ids: List[str]


class CategoryRuleBase(BaseModel):
    name: str
    category: str
    keywords: List[str]
    # only_uncategorized removed as it's not in DB model
    priority: int = 0
    is_transfer: bool = False
    to_account_id: Optional[str] = None
    exclude_from_reports: bool = False

class CategoryRuleCreate(CategoryRuleBase):
    pass

class CategoryRuleUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    keywords: Optional[List[str]] = None
    priority: Optional[int] = None
    is_transfer: Optional[bool] = None
    to_account_id: Optional[str] = None
    exclude_from_reports: Optional[bool] = None

class CategoryRuleRead(CategoryRuleBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

class RuleSuggestion(BaseModel):
    name: str
    category: str
    keywords: List[str]
    only_uncategorized: bool = True
    confidence: int

class IgnoredSuggestionCreate(BaseModel):
    pattern: str

class CategoryBase(BaseModel):
    name: str
    type: str = "expense"
    icon: Optional[str] = "🏷️"
    color: Optional[str] = "#3B82F6"
    parent_id: Optional[str] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    parent_id: Optional[str] = None

class CategoryRead(CategoryBase):
    id: str
    tenant_id: str
    parent_name: Optional[str] = None
    subcategories: List['CategoryRead'] = []
    
    class Config:
        from_attributes = True

# Expense Groups
class ExpenseGroupBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: bool = True
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    budget: Optional[float] = 0.0
    icon: Optional[str] = None

class ExpenseGroupCreate(ExpenseGroupBase):
    pass

class ExpenseGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    budget: Optional[float] = None
    icon: Optional[str] = None

class ExpenseGroupRead(ExpenseGroupBase):
    id: str
    tenant_id: str
    created_at: datetime
    total_spend: Optional[float] = 0.0

    class Config:
        from_attributes = True

class BudgetBase(BaseModel):
    category: str
    amount_limit: Decimal
    period: str = "MONTHLY"

class BudgetCreate(BudgetBase):
    pass

class BudgetUpdate(BaseModel):
    amount_limit: Optional[Decimal] = None

class BudgetRead(BudgetBase):
    id: Union[UUID, str]
    tenant_id: Union[UUID, str]
    updated_at: Optional[datetime] = None
    
    # UI Helpers
    type: str = "expense"
    icon: str = "🏷️"
    color: str = "#3B82F6"
    parent_id: Optional[str] = None
    category_id: Optional[str] = None

    class Config:
        from_attributes = True

class BudgetProgress(BudgetRead):
    spent: Decimal
    remaining: Decimal
    percentage: float

class CategoryBudgetProgress(BaseModel):
    id: Optional[Union[UUID, str]] = None # Backward compatibility
    budget_id: Optional[Union[UUID, str]] = None
    tenant_id: Optional[Union[UUID, str]] = None
    category: str
    amount_limit: Optional[Decimal] = None
    spent: Decimal
    income: Decimal = Decimal('0.0')
    remaining: Optional[Decimal] = None
    percentage: Optional[float] = None
    period: str = "MONTHLY"
    updated_at: Optional[datetime] = None
    total_excluded: Optional[Decimal] = Decimal('0.0')
    excluded_income: Optional[Decimal] = Decimal('0.0')
    type: str = "expense"
    icon: Optional[str] = "🏷️"
    color: Optional[str] = "#3B82F6"
    parent_id: Optional[str] = None
    category_id: Optional[str] = None

class BudgetOverview(BaseModel):
    category: str = "OVERALL"
    amount_limit: Optional[Decimal] = None
    spent: Decimal
    income: Decimal = Decimal('0.0')
    remaining: Optional[Decimal] = None
    percentage: Optional[float] = None
    total_excluded: Optional[Decimal] = Decimal('0.0')
    excluded: Optional[Decimal] = Decimal('0.0') # For backward compatibility
    excluded_income: Optional[Decimal] = Decimal('0.0')
    updated_at: Optional[datetime] = None
    icon: str = "🏁"
    color: str = "#10B981"

class SmartCategorizeRequest(BaseModel):
    transaction_id: str
    category: str
    create_rule: bool = False
    apply_to_similar: bool = False
    exclude_from_reports: bool = False

class Frequency(str): 
    # Helper for frontend types, though we validated via Enum in models
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"

class RecurringTransactionBase(BaseModel):
    name: str
    amount: Decimal
    account_id: Union[UUID, str]
    category: Optional[str] = None
    frequency: str = "MONTHLY" 
    start_date: datetime
    next_run_date: datetime
    is_active: bool = True
    exclude_from_reports: bool = False

class RecurringTransactionCreate(RecurringTransactionBase):
    pass

class RecurringTransactionUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[Decimal] = None
    account_id: Optional[Union[UUID, str]] = None
    category: Optional[str] = None
    frequency: Optional[str] = None
    start_date: Optional[datetime] = None
    next_run_date: Optional[datetime] = None
    is_active: Optional[bool] = None
    exclude_from_reports: Optional[bool] = None

class RecurringTransactionRead(RecurringTransactionBase):
    id: Union[UUID, str]
    tenant_id: Union[UUID, str]
    last_run_date: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
        
# --- Loan Schemas ---

class LoanBase(BaseModel):
    name: str # Mapped to Account.name
    principal_amount: Decimal
    interest_rate: Decimal
    start_date: datetime
    tenure_months: int
    emi_amount: Decimal
    emi_date: int
    loan_type: str = "OTHER"
    bank_account_id: Optional[Union[UUID, str]] = None

class LoanCreate(LoanBase):
    pass

class LoanRead(LoanBase):
    id: Union[UUID, str]
    tenant_id: Union[UUID, str]
    account_id: Union[UUID, str]
    
    # Computed fields
    outstanding_balance: Decimal = Decimal('0.0')
    paid_principal: Decimal = Decimal('0.0')
    progress_percentage: float = 0.0
    next_emi_date: Optional[datetime] = None
    
    created_at: datetime
    
    class Config:
        from_attributes = True

class AmortizationScheduleItem(BaseModel):
    installment_no: int
    due_date: datetime
    opening_balance: Decimal
    emi: Decimal
    principal_component: Decimal
    interest_component: Decimal
    closing_balance: Decimal
    status: str = "PENDING" # PAID, PENDING, OVERDUE

class LoanDetail(LoanRead):
    amortization_schedule: List[AmortizationScheduleItem]

class LoanRepayment(BaseModel):
    bank_account_id: Union[UUID, str]
    amount: Decimal
    date: datetime
    installment_no: Optional[int] = None
    description: Optional[str] = None

# Investment Goals
class InvestmentGoalBase(BaseModel):
    name: str
    target_amount: Decimal
    target_date: Optional[datetime] = None
    icon: str = "🎯"
    color: str = "#3b82f6"
    is_completed: bool = False

class InvestmentGoalCreate(InvestmentGoalBase):
    pass

class InvestmentGoalUpdate(BaseModel):
    name: Optional[str] = None
    target_amount: Optional[Decimal] = None
    target_date: Optional[datetime] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    is_completed: Optional[bool] = None

class GoalAssetBase(BaseModel):
    type: str  # MUTUAL_FUND, BANK_ACCOUNT, MANUAL
    name: Optional[str] = None
    manual_amount: Optional[Decimal] = None
    interest_rate: Optional[Decimal] = None
    linked_account_id: Optional[str] = None

class GoalAssetCreate(GoalAssetBase):
    pass

class GoalAssetRead(GoalAssetBase):
    id: str
    goal_id: str
    display_name: str = ""
    current_value: Decimal = Decimal('0.0')
    created_at: datetime
    
    class Config:
        from_attributes = True

class GoalHoldingRead(BaseModel):
    id: str
    scheme_name: str
    folio_number: Optional[str] = None
    current_value: Decimal = Decimal('0.0')

    class Config:
        from_attributes = True

class InvestmentGoalRead(InvestmentGoalBase):
    id: str
    tenant_id: str
    created_at: datetime
    assets: List[GoalAssetRead] = []

    class Config:
        from_attributes = True

class InvestmentGoalProgress(InvestmentGoalRead):
    holdings: List[GoalHoldingRead] = []
    current_amount: Decimal = Decimal('0.0')
    remaining_amount: Decimal = Decimal('0.0')
    progress_percentage: float = 0.0
    holdings_count: int = 0

class MatchCountRequest(BaseModel):
    keywords: List[str]
    only_uncategorized: bool = True
class BulkRenameRequest(BaseModel):
    old_name: str
    new_name: str
    sync_to_parser: bool = False
