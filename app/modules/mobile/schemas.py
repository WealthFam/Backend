from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class DeviceBase(BaseModel):
    device_id: str
    device_name: str

class DeviceResponse(DeviceBase):
    id: str
    tenant_id: str
    is_approved: bool
    is_enabled: bool
    is_ignored: bool
    last_seen_at: datetime
    created_at: datetime
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    user_avatar: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class DeviceRegister(BaseModel):
    device_id: str
    device_name: str
    fcm_token: Optional[str] = None

class MobileLoginRequest(BaseModel):
    username: str
    password: str
    device_id: str
    device_name: str

class MobileLoginResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    device_status: DeviceResponse
    user_role: Optional[str] = "ADULT"
    user_name: Optional[str] = None
    user_avatar: Optional[str] = None

class ToggleApprovalRequest(BaseModel):
    is_approved: bool

class ToggleEnabledRequest(BaseModel):
    is_enabled: bool

class AssignUserRequest(BaseModel):
    user_id: Optional[str] = None

class DeviceUpdate(BaseModel):
    device_name: Optional[str] = None
    is_enabled: Optional[bool] = None
    is_ignored: Optional[bool] = None
    user_id: Optional[str] = None

class DashboardSummary(BaseModel):
    today_total: float
    yesterday_total: float = 0.0
    last_month_same_day_total: float = 0.0
    monthly_total: float
    currency: str = "INR"
    daily_budget_limit: float = 0.0
    prorated_budget: float = 0.0

class BudgetSummary(BaseModel):
    limit: float
    spent: float
    percentage: float

class CategorySpending(BaseModel):
    name: str
    amount: float

class RecentTransaction(BaseModel):
    id: str
    date: datetime
    description: str
    amount: float
    category: str
    account_name: Optional[str] = None
    account_owner_name: Optional[str] = None
    is_hidden: bool = False
    expense_group_id: Optional[str] = None
    expense_group_name: Optional[str] = None
    source: Optional[str] = None
    has_documents: bool = False

class SpendingTrendItem(BaseModel):
    date: str
    amount: float
    daily_limit: float

class CategoryPieItem(BaseModel):
    name: str
    value: float
    color: Optional[str] = None

class MonthTrendItem(BaseModel):
    month: str
    spent: float
    budget: float
    is_selected: bool = False

class InvestmentSummary(BaseModel):
    total_invested: float
    current_value: float
    profit_loss: float
    xirr: Optional[float] = None
    sparkline: List[float] = []
    day_change: float = 0.0
    day_change_percent: float = 0.0

class MobileDashboardResponse(BaseModel):
    summary: DashboardSummary
    budget: BudgetSummary
    investment_summary: Optional[InvestmentSummary] = None
    spending_trend: List[SpendingTrendItem]
    category_distribution: List[CategoryPieItem]
    month_wise_trend: List[MonthTrendItem] = []
    recent_transactions: List[RecentTransaction]
    pending_triage_count: int = 0
    family_members_count: Optional[int] = None

class DashboardSummaryResponse(BaseModel):
    summary: DashboardSummary
    budget: BudgetSummary
    recent_transactions: List[RecentTransaction]
    pending_triage_count: int
    pending_training_count: int
    family_members_count: int

class DashboardTrendsResponse(BaseModel):
    month_wise_trend: List[MonthTrendItem]
    spending_trend: List[SpendingTrendItem]

class DashboardCategoriesResponse(BaseModel):
    category_distribution: List[CategoryPieItem]

class DashboardInvestmentsResponse(BaseModel):
    investment_summary: Optional[InvestmentSummary]

class MemberResponse(BaseModel):
    id: str
    name: str
    role: str
    avatar_url: Optional[str] = None

class TransactionResponse(BaseModel):
    data: List[RecentTransaction]
    next_page: Optional[int] = None

class FundHolding(BaseModel):
    scheme_code: str
    scheme_name: str
    units: float
    current_value: float
    invested_value: float
    profit_loss: float
    day_change: Optional[float] = 0.0
    day_change_percentage: Optional[float] = 0.0
    last_updated: str
    xirr: Optional[float] = None
    allocation_percentage: Optional[float] = None

class MobileFundsResponse(BaseModel):
    total_invested: float
    total_current: float
    day_change: Optional[float] = 0.0
    day_change_percentage: Optional[float] = 0.0
    total_pl: float
    xirr: Optional[float] = None
    holdings: List[FundHolding]

class Category(BaseModel):
    id: str
    name: str
    icon: Optional[str] = None
    type: str = "expense"
    parent_id: Optional[str] = None
    subcategories: List['Category'] = []

    model_config = ConfigDict(from_attributes=True)

class UpdateTransactionCategoryRequest(BaseModel):
    category: str
    create_rule: bool = False
    rule_keywords: Optional[List[str]] = None

Category.model_rebuild()
