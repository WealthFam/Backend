import json
from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional, Union, Annotated
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator, BeforeValidator

# --- Finance Coercion Utilities (PRACTICES.md Section 11.2) ---
# Critical for parsing financial data from UI sliders or legacy CSV inputs 
# where numeric types might arrive as strings or floats.

def coerce_int(v: Any) -> Any:
    """Ensure integer types are coerced correctly before strict validation."""
    if v is None: return None
    try:
        return int(v)
    except (ValueError, TypeError):
        return v

StrictInt = Annotated[int, BeforeValidator(coerce_int)]

def coerce_decimal(v: Any) -> Any:
    """Proactively convert floats/ints to Decimals to prevent precision loss."""
    if v is None: return None
    if isinstance(v, (int, float)):
        return Decimal(str(v))
    return v

# Hardened Financial Types: Maintains high-precision math while allowing API flexibility.
StrictDecimal = Annotated[Decimal, BeforeValidator(coerce_decimal)]

from backend.app.modules.finance.models import AccountType, TransactionType, StatementStatus, StatementSource

class AccountBase(BaseModel):
    name: str
    type: AccountType
    currency: str = "INR"
    account_mask: Optional[str] = None
    balance: Optional[Decimal] = Decimal('0.0')
    credit_limit: Optional[Decimal] = None
    billing_day: Optional[StrictInt] = None
    due_day: Optional[StrictInt] = None
    is_verified: bool = True
    import_config: Optional[str] = None

class AccountCreate(AccountBase):
    owner_id: Optional[Union[UUID, str]] = None

    tenant_id: Optional[Union[UUID, str]] = None # Allow specifying a tenant

class AccountUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[AccountType] = None
    currency: Optional[str] = None
    account_mask: Optional[str] = None

    owner_id: Optional[Union[UUID, str]] = None
    balance: Optional[Decimal] = None
    credit_limit: Optional[Decimal] = None
    billing_day: Optional[StrictInt] = None
    due_day: Optional[StrictInt] = None
    is_verified: Optional[bool] = None
    import_config: Optional[str] = None
    tenant_id: Optional[Union[UUID, str]] = None


class AccountRead(AccountBase):
    id: Union[UUID, str]
    tenant_id: Union[UUID, str]
    owner_id: Optional[Union[UUID, str]] = None
    linked_goals: List[str] = []

    created_at: datetime
    
    last_synced_balance: Optional[Decimal] = None
    last_synced_at: Optional[datetime] = None
    last_synced_limit: Optional[Decimal] = None

    model_config = ConfigDict(from_attributes=True, strict=True)

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
    exclude_from_reports: bool = False
    is_emi: bool = False
    loan_id: Optional[str] = None
    expense_group_id: Optional[str] = None

    @field_validator('tags', mode='before')
    @classmethod
    def parse_tags(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except:
                return []
        return v or []

class TransactionCreate(TransactionBase):
    account_id: Union[UUID, str]
    external_id: Optional[str] = None
    source: Optional[str] = "MANUAL"
    is_transfer: bool = False
    to_account_id: Optional[str] = None
    content_hash: Optional[str] = None
    
    # Mutual Fund Specific Fields
    scheme_code: Optional[str] = None
    folio_number: Optional[str] = None
    nav: Optional[Decimal] = None
    units: Optional[Decimal] = None
    type: Optional[str] = None

class TransactionUpdate(BaseModel):
    description: Optional[str] = None
    recipient: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    date: Optional[datetime] = None
    amount: Optional[Decimal] = None
    account_id: Optional[Union[UUID, str]] = None
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

    model_config = ConfigDict(from_attributes=True, strict=True)

class TransactionRead(TransactionBase):
    id: Union[UUID, str]
    account_id: Union[UUID, str]
    tenant_id: Union[UUID, str]
    type: Optional[str] = "DEBIT"
    source: Optional[str] = "MANUAL"
    external_id: Optional[str] = None
    content_hash: Optional[str] = None
    transfer_account_id: Optional[Union[UUID, str]] = None
    exclude_from_reports: bool = False
    is_emi: bool = False
    loan_id: Optional[str] = None
    expense_group_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, strict=True)

class TransactionPagination(BaseModel):
    data: List[TransactionRead]
    total: int
    page: int
    size: int

class BulkDeleteRequest(BaseModel):
    transaction_ids: List[str]


class CategoryRuleBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, strict=True)

    name: str = Field(description="Human-readable name for the rule")
    category: str = Field(description="The category to assign if matched")
    keywords: List[str] = Field(description="List of strings to match against transaction text")
    priority: int = Field(default=0, description="Execution priority (higher numbers run first)")
    is_transfer: bool = Field(default=False, description="If true, marks matched transactions as transfers")
    to_account_id: Optional[str] = Field(default=None, description="Optional destination account for transfers")
    exclude_from_reports: bool = Field(default=False, description="If true, matched transactions are hidden from reports")

    @field_validator('keywords')
    @classmethod
    def validate_keywords(cls, v):
        # Soften validator: Allow empty list for READ operations 
        # (Application layer handles is_valid=False for empty rules)
        if v is None:
            return []
        
        cleaned = []
        for kw in v:
            val = kw.strip()
            if len(val) >= 3:
                cleaned.append(val)
        return cleaned

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
    id: Union[UUID, str]
    tenant_id: Union[UUID, str]
    is_valid: bool = Field(default=True, description="Indicates if the rule is currently functional")
    validation_error: Optional[str] = Field(default=None, description="Human-readable reason for validation failure")
    hit_count: int = Field(default=0, description="Total number of transactions matched by this rule")
    last_hit_at: Optional[datetime] = Field(default=None, description="Timestamp of last successful rule application")
    created_at: datetime

class CategoryRulePagination(BaseModel):
    model_config = ConfigDict(strict=True)
    data: List[CategoryRuleRead]
    total: int

# --- Triage Detection Schemas ---
class TriageScanResult(BaseModel):
    """Result of scanning a single rule against the triage queue."""
    rule_id: str
    rule_name: str
    category: str
    matching_count: int
    preview: List[dict] = []

class TriageScanSummary(BaseModel):
    """Aggregate result of scanning all rules against the triage queue."""
    total_pending: int
    total_matches: int
    rules_with_matches: List[TriageScanResult]

class RuleStatsResponse(BaseModel):
    """Aggregate rule performance statistics."""
    total_rules: int
    total_hits: int
    rules_with_zero_hits: int
    avg_hit_rate: float
    top_rules: List[dict] = []
    pending_triage: int = 0

class RuleSuggestion(BaseModel):
    name: str
    category: str
    keywords: List[str]
    only_uncategorized: bool = True
    count: int = 1
    confidence: float = 0.5
    confidence_level: str = "Medium" # Low, Medium, High
    reason: Optional[str] = None

class IgnoredRecurringPatternCreate(BaseModel):
    pattern: str

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
    
    model_config = ConfigDict(from_attributes=True, strict=True)

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

    model_config = ConfigDict(from_attributes=True, strict=True)

class BulkLinkTransactionsRequest(BaseModel):
    transaction_ids: List[str]

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

    model_config = ConfigDict(from_attributes=True, strict=True)

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
    is_transfer: Optional[bool] = False
    to_account_id: Optional[str] = None

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
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None

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
    
    model_config = ConfigDict(from_attributes=True, strict=True)

class HistoryPoint(BaseModel):
    date: datetime
    amount: Decimal

class RecurringSuggestion(BaseModel):
    name: str
    amount: Decimal
    frequency: str  # MONTHLY, WEEKLY, QUARTERLY, etc.
    category: Optional[str] = None
    account_id: str
    confidence: float
    reason: str
    last_date: datetime
    pattern: Optional[str] = None # The exact merchant/keyword detected
    detected_count: int = 0
    recent_history: List[HistoryPoint] = []
        
# --- Loan Schemas ---

class LoanBase(BaseModel):
    name: str # Mapped to Account.name
    principal_amount: Decimal
    interest_rate: Decimal
    start_date: datetime
    tenure_months: StrictInt
    emi_amount: Decimal
    emi_date: StrictInt
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
    
    model_config = ConfigDict(from_attributes=True, strict=True)

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
    amount: StrictDecimal
    date: datetime
    installment_no: Optional[int] = None
    description: Optional[str] = None

class LoanSimulationRequest(BaseModel):
    extra_monthly_payment: StrictDecimal = Field(default=Decimal("0"))
    one_time_prepayment: StrictDecimal = Field(default=Decimal("0"))

    model_config = ConfigDict(strict=True)

class LoanSimulationResult(BaseModel):
    months_saved: int
    interest_saved: StrictDecimal
    new_total_interest: StrictDecimal
    new_months: int
    custom_schedule: List[Any] = []
    standard_schedule: List[Any] = []

    model_config = ConfigDict(strict=True)

# Investment Goals
class InvestmentGoalBase(BaseModel):
    name: str
    target_amount: Decimal
    target_date: Optional[datetime] = None
    icon: str = "🎯"
    color: str = "#3b82f6"
    is_completed: bool = False
    owner_id: Optional[str] = None

class InvestmentGoalCreate(InvestmentGoalBase):
    pass

class InvestmentGoalUpdate(BaseModel):
    name: Optional[str] = None
    target_amount: Optional[Decimal] = None
    target_date: Optional[datetime] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    is_completed: Optional[bool] = None
    owner_id: Optional[str] = None

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
    
    model_config = ConfigDict(from_attributes=True, strict=True)

class GoalHoldingRead(BaseModel):
    id: str
    scheme_name: str
    folio_number: Optional[str] = None
    current_value: Decimal = Decimal('0.0')

    model_config = ConfigDict(from_attributes=True, strict=True)

class InvestmentGoalRead(InvestmentGoalBase):
    id: str
    tenant_id: str
    owner_id: Optional[str] = None
    created_at: datetime
    assets: List[GoalAssetRead] = []

    model_config = ConfigDict(from_attributes=True, strict=True)

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

class BalanceSnapshotBase(BaseModel):
    account_id: Union[UUID, str]
    balance: Decimal
    credit_limit: Optional[Decimal] = None
    timestamp: datetime
    source: str = "MANUAL"

class BalanceSnapshotCreate(BalanceSnapshotBase):
    tenant_id: Optional[Union[UUID, str]] = None

class BalanceSnapshotRead(BalanceSnapshotBase):
    id: Union[UUID, str]
    tenant_id: Union[UUID, str]

    model_config = ConfigDict(from_attributes=True, strict=True)

class SpendingForecastDay(BaseModel):
    date: str
    is_forecast: bool
    stacks: dict[str, Decimal] = {} # user_id/name -> amount

class SpendingForecastResponse(BaseModel):
    user_names: dict[str, str]
    trend: List[SpendingForecastDay]
    daily_burn_rate: Decimal
    forecast_total: Decimal

class MutualFundBenchmarkRuleBase(BaseModel):
    priority: int = Field(default=0, description="Execution priority (lower is higher)")
    keyword: str = Field(description="Keyword to match against fund category/name")
    benchmark_symbol: str = Field(description="MFAPI scheme code for the benchmark index")
    benchmark_label: str = Field(description="Display label for the benchmark index")
    styling_color: Optional[str] = Field(default="#3B82F6", description="Hex color for the benchmark line")
    styling_style: str = Field(default="solid", description="Line style: solid, dashed, dotted")
    styling_dash_array: Optional[str] = Field(default=None, description="SVG dash array for dashed lines")

class MutualFundBenchmarkRuleCreate(MutualFundBenchmarkRuleBase):
    pass

class MutualFundBenchmarkRuleUpdate(BaseModel):
    priority: Optional[int] = None
    keyword: Optional[str] = None
    benchmark_symbol: Optional[str] = None
    benchmark_label: Optional[str] = None
    styling_color: Optional[str] = None
    styling_style: Optional[str] = None
    styling_dash_array: Optional[str] = None

class MutualFundBenchmarkRuleRead(MutualFundBenchmarkRuleBase):
    id: Union[UUID, str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True, strict=True)

class MutualFundBenchmarkRulePagination(BaseModel):
    data: List[MutualFundBenchmarkRuleRead]
    total: int
    model_config = ConfigDict(strict=True)

class MarketIndexItem(BaseModel):
    name: str
    value: str
    change: str
    percent: str
    isUp: bool
    sparkline: List[float] = []
    labels: List[str] = []

class MarketIndexResponse(BaseModel):
    data: List[MarketIndexItem]
    model_config = ConfigDict(strict=True)

class MutualFundMasterRead(BaseModel):
    scheme_code: Union[str, int]
    scheme_name: str
    isin_growth: Optional[str] = None
    fund_house: Optional[str] = None
    category: Optional[str] = None
    nav: Optional[Decimal] = None
    returns_3y: Optional[Decimal] = None
    risk_level: str = "Moderate"
    aum: Optional[str] = None
    trending: bool = False
    
    model_config = ConfigDict(from_attributes=True)

class MutualFundSearchResponse(BaseModel):
    data: List[MutualFundMasterRead]
    total: int
    page: int
    limit: int
    model_config = ConfigDict()

class MutualFundHoldingRead(BaseModel):
    id: Union[UUID, str]
    scheme_code: Union[str, int]
    scheme_name: str
    folio_number: Optional[str] = None
    units: Decimal
    average_price: Decimal
    current_value: Decimal
    invested_value: Decimal
    last_nav: Optional[Decimal] = None
    category: Optional[str] = None
    profit_loss: Decimal
    profit_loss_pct: float
    last_updated_at: Union[datetime, str]
    has_multiple: bool = False
    children: List[Any] = []
    sparkline: List[float] = []
    
    model_config = ConfigDict(from_attributes=True)

class PortfolioOverviewResponse(BaseModel):
    data: List[MutualFundHoldingRead]
    total_invested: Decimal
    total_current: Decimal
    total_pl: Decimal
    overall_xirr: Optional[float] = None
    model_config = ConfigDict()

class CreditCardBillPay(BaseModel):
    source_account_id: Union[UUID, str]
    amount: Decimal
    date: datetime
    description: Optional[str] = "Credit Card Bill Payment"

CategoryRead.model_rebuild()

class StatementTransactionRead(BaseModel):
    id: str
    statement_id: str
    date: datetime
    amount: Decimal
    type: TransactionType
    description: str
    ref_id: Optional[str] = None
    category_suggestion: Optional[str] = None
    is_reconciled: bool = False
    matched_transaction_id: Optional[str] = None
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class StatementRead(BaseModel):
    id: str
    account_id: Optional[str] = None
    vault_id: Optional[str] = None
    filename: str
    status: StatementStatus
    source: StatementSource
    email_sender: Optional[str] = None
    created_at: datetime
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    
    transactions: List[StatementTransactionRead] = []

    model_config = ConfigDict(from_attributes=True)

class PaginatedStatementRead(BaseModel):
    items: List[StatementRead]
    total: int

class PaginatedStatementTransactionRead(BaseModel):
    items: List[StatementTransactionRead]
    total: int

class BulkIngestRequestItem(BaseModel):
    transaction_id: str
    category: Optional[str] = None
    create_rule: bool = True
    exclude_from_reports: bool = False

class BulkIngestRequest(BaseModel):
    items: List[BulkIngestRequestItem]
